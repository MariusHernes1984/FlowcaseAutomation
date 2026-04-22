"""Project/reference discovery across CVs.

Flowcase doesn't expose a standalone /projects endpoint — project
experiences live inside each consultant's CV under ``project_experiences``.
This module walks that dataset to produce a project-centric view:

    list_customers(query) -> list of {id, name}
    list_industries(query) -> list of {id, name}
    find_projects(filters) -> list of aggregated "deliveries"

An aggregated delivery groups project entries that look like the same
real-world engagement (same customer + overlapping timeline) and keeps
the list of consultants who contributed.

Cost: ``find_projects`` fetches up to ``max_candidates`` CVs in parallel.
The client caches CVs for 10 minutes, so repeat queries are cheap.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Iterable

from flowcase_mcp.client import FlowcaseClient
from flowcase_mcp.formatting import pick_lang

logger = logging.getLogger(__name__)


MAX_CANDIDATE_CVS = 80  # hard cap on CVs we open per find_projects call
PARALLEL_CV_FETCHES = 8


# ---------------------------------------------------------------------------
# Customer / industry helpers
# ---------------------------------------------------------------------------


def _data_export_name(item: dict[str, Any], lang: str) -> str:
    """Extract a display name from a data_export record."""
    # The shape is {"id": "...", "values": {"no": "...", ...}} OR simpler.
    values = item.get("values")
    if isinstance(values, dict):
        return pick_lang(values, lang)
    name = item.get("name")
    if isinstance(name, str):
        return name
    return ""


def filter_list_by_query(
    items: list[dict[str, Any]], query: str | None, lang: str
) -> list[dict[str, Any]]:
    if not query:
        return items
    q = query.strip().lower()
    if not q:
        return items
    out: list[dict[str, Any]] = []
    for item in items:
        name = _data_export_name(item, lang).lower()
        if q in name:
            out.append(item)
    return out


async def list_customers_compact(
    client: FlowcaseClient,
    *,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
    lang: str = "no",
) -> dict[str, Any]:
    items = await client.get_customers()
    filtered = filter_list_by_query(items, query, lang)
    filtered.sort(key=lambda x: _data_export_name(x, lang).lower())
    page = filtered[offset : offset + limit]
    return {
        "total": len(filtered),
        "count": len(page),
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(page) < len(filtered),
        "customers": [
            {"customer_id": it.get("id") or it.get("_id"), "name": _data_export_name(it, lang)}
            for it in page
        ],
    }


async def list_industries_compact(
    client: FlowcaseClient,
    *,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
    lang: str = "no",
) -> dict[str, Any]:
    items = await client.get_industries()
    filtered = filter_list_by_query(items, query, lang)
    filtered.sort(key=lambda x: _data_export_name(x, lang).lower())
    page = filtered[offset : offset + limit]
    return {
        "total": len(filtered),
        "count": len(page),
        "offset": offset,
        "limit": limit,
        "has_more": offset + len(page) < len(filtered),
        "industries": [
            {
                "industry_id": it.get("id") or it.get("_id"),
                "name": _data_export_name(it, lang),
            }
            for it in page
        ],
    }


# ---------------------------------------------------------------------------
# find_projects
# ---------------------------------------------------------------------------


_OBJECT_ID_RE = re.compile(r"^[0-9a-f]{24}$", re.IGNORECASE)
_CUSTOMER_SUFFIXES = (" asa", " as", " ab", " a/s", " sa", " inc", " llc", " ltd", " gmbh")


def _normalize_customer(raw: str | None) -> str:
    if not raw:
        return ""
    s = raw.strip().lower()
    for suf in _CUSTOMER_SUFFIXES:
        if s.endswith(suf):
            s = s[: -len(suf)].strip()
    # collapse whitespace
    return " ".join(s.split())


def _yearmonth(year: Any, month: Any) -> tuple[int, int] | None:
    """Parse year/month strings to (year, month). Month falls back to 1."""
    try:
        y = int(year) if year not in (None, "") else None
        if y is None:
            return None
    except (TypeError, ValueError):
        return None
    try:
        m = int(month) if month not in (None, "") else 1
    except (TypeError, ValueError):
        m = 1
    if m < 1 or m > 12:
        m = 1
    return (y, m)


def _months_between(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs((a[0] - b[0]) * 12 + (a[1] - b[1]))


def _overlaps(
    a_from: tuple[int, int] | None,
    a_to: tuple[int, int] | None,
    b_from: tuple[int, int] | None,
    b_to: tuple[int, int] | None,
    *,
    buffer_months: int = 3,
) -> bool:
    """Two date ranges overlap (or are within buffer months of touching)."""
    if not (a_from and b_from):
        return False
    # Treat missing end as "ongoing" — pretend end = from + 60 months
    a_end = a_to or (a_from[0] + 5, a_from[1])
    b_end = b_to or (b_from[0] + 5, b_from[1])
    # Convert to month counters
    def to_n(t: tuple[int, int]) -> int:
        return t[0] * 12 + t[1]
    a1, a2 = to_n(a_from), to_n(a_end)
    b1, b2 = to_n(b_from), to_n(b_end)
    return a1 <= b2 + buffer_months and b1 <= a2 + buffer_months


def _project_matches_filters(
    proj: dict[str, Any],
    *,
    industry_ids: set[str] | None,
    customer_names_norm: set[str],
    skill_ids: set[str] | None,
    description_contains: str | None,
    since_year: int | None,
    lang: str,
) -> bool:
    # Since-year gate
    y_from = proj.get("year_from")
    if since_year is not None and y_from:
        try:
            if int(y_from) < since_year:
                return False
        except (TypeError, ValueError):
            pass

    # Industry filter — CV projects store `industry` as multilang dict;
    # there's no industry_id on the project. Match on name against the
    # resolved industry name set instead.
    if industry_ids:
        # industry_ids is actually name-set here — see find_projects()
        project_industry = _normalize_customer(pick_lang(proj.get("industry"), lang))
        if not project_industry or project_industry not in industry_ids:
            return False

    # Customer filter — similar, by normalized name
    if customer_names_norm:
        project_customer = _normalize_customer(pick_lang(proj.get("customer"), lang))
        if project_customer not in customer_names_norm:
            return False

    # Skill filter — project_experience_skills[].tags (multilang)
    if skill_ids:
        pes = proj.get("project_experience_skills") or []
        # We don't have skill_ids directly on the project, only skill tags.
        # This means we can only pre-filter by skill when we have the
        # resolved skill NAMES too. The caller passes tag names here
        # (normalized lowercase) instead of IDs.
        project_skill_names = {
            pick_lang(s.get("tags"), lang).strip().lower()
            for s in pes
            if isinstance(s, dict)
        }
        project_skill_names.discard("")
        if not project_skill_names & skill_ids:
            return False

    # Free-text filter
    if description_contains:
        needle = description_contains.strip().lower()
        if needle:
            haystack_parts: list[str] = []
            for key in ("description", "long_description", "customer_description"):
                haystack_parts.append(pick_lang(proj.get(key), lang))
            for role in proj.get("roles") or []:
                if isinstance(role, dict):
                    haystack_parts.append(pick_lang(role.get("long_description"), lang))
            haystack = "\n".join(haystack_parts).lower()
            if needle not in haystack:
                return False

    return True


async def _resolve_industry_names(
    client: FlowcaseClient, raw: Iterable[str] | None, lang: str
) -> tuple[set[str], list[str]]:
    """Given user input (names), return (resolved_normalized_names, unresolved)."""
    if not raw:
        return set(), []
    taxonomy = await client.get_industries()
    by_norm: dict[str, str] = {}
    for item in taxonomy:
        name = _data_export_name(item, lang)
        if name:
            by_norm[_normalize_customer(name)] = name

    resolved: set[str] = set()
    unresolved: list[str] = []
    for q in raw:
        if not q:
            continue
        norm = _normalize_customer(q)
        if norm in by_norm:
            resolved.add(norm)
            continue
        # substring fallback — accept any industry whose name contains q
        hits = [k for k in by_norm if norm in k]
        if hits:
            resolved.update(hits)
        else:
            unresolved.append(q)
    return resolved, unresolved


async def _resolve_customer_names(
    client: FlowcaseClient, raw: Iterable[str] | None, lang: str
) -> tuple[set[str], list[str]]:
    if not raw:
        return set(), []
    taxonomy = await client.get_customers()
    by_norm: dict[str, str] = {}
    for item in taxonomy:
        name = _data_export_name(item, lang)
        if name:
            by_norm[_normalize_customer(name)] = name

    resolved: set[str] = set()
    unresolved: list[str] = []
    for q in raw:
        if not q:
            continue
        norm = _normalize_customer(q)
        if norm in by_norm:
            resolved.add(norm)
            continue
        hits = [k for k in by_norm if norm in k]
        if hits:
            resolved.update(hits)
        else:
            unresolved.append(q)
    return resolved, unresolved


async def _resolve_skill_names_and_ids(
    client: FlowcaseClient, raw: Iterable[str] | None, lang: str
) -> tuple[set[str], set[str], list[str]]:
    """Return (skill_ids, normalized_skill_names, unresolved)."""
    if not raw:
        return set(), set(), []
    taxonomy = await client.get_skill_taxonomy()
    id_by_norm: dict[str, str] = {}
    name_by_id: dict[str, str] = {}
    for s in taxonomy:
        sid = s.get("_id")
        values = s.get("values") or {}
        if not sid or not isinstance(values, dict):
            continue
        for v in values.values():
            if isinstance(v, str) and v.strip():
                id_by_norm[v.strip().lower()] = sid
                break  # any language entry is enough for name matching
        # keep the preferred-language display name for output
        name_by_id[sid] = pick_lang(values, lang) or sid

    ids: set[str] = set()
    names: set[str] = set()
    unresolved: list[str] = []
    for q in raw:
        if not q:
            continue
        text = q.strip()
        if _OBJECT_ID_RE.match(text):
            ids.add(text.lower())
            lower_name = (name_by_id.get(text) or "").lower()
            if lower_name:
                names.add(lower_name)
            continue
        lowered = text.lower()
        if lowered in id_by_norm:
            ids.add(id_by_norm[lowered])
            names.add(lowered)
            continue
        # substring
        matches = [(nm, id_by_norm[nm]) for nm in id_by_norm if lowered in nm]
        if matches:
            for nm, sid in matches:
                ids.add(sid)
                names.add(nm)
        else:
            unresolved.append(text)
    return ids, names, unresolved


def _candidate_score(
    user: dict[str, Any],
    industry_ids: set[str],
    customer_ids: set[str],
    skill_ids: set[str],
) -> int:
    """Heuristic — more filter signals present on the user's record = higher."""
    score = 0
    user_industries = set(user.get("industries") or [])
    user_customers = set(user.get("customers") or [])
    user_skills = set(user.get("skills") or [])
    if industry_ids:
        score += 3 * len(industry_ids & user_industries)
    if customer_ids:
        score += 4 * len(customer_ids & user_customers)
    if skill_ids:
        score += 2 * len(skill_ids & user_skills)
    return score


def _project_key(proj: dict[str, Any], lang: str) -> tuple[str, tuple[int, int] | None]:
    customer_norm = _normalize_customer(pick_lang(proj.get("customer"), lang))
    date = _yearmonth(proj.get("year_from"), proj.get("month_from"))
    return (customer_norm, date)


def _aggregate_projects(
    raw_projects: list[dict[str, Any]], lang: str
) -> list[dict[str, Any]]:
    """Cluster projects by normalized customer + overlapping dates."""
    clusters: list[dict[str, Any]] = []
    for entry in raw_projects:
        merged = False
        c_norm = entry["_customer_norm"]
        for c in clusters:
            if c["_customer_norm"] != c_norm:
                continue
            if _overlaps(
                entry["_from"], entry["_to"], c["_from"], c["_to"], buffer_months=3
            ):
                c["consultants"].append(entry["consultant"])
                c["roles"].update(entry["roles_set"])
                c["skills"].update(entry["skills_set"])
                # widen date range
                if entry["_from"] and (not c["_from"] or entry["_from"] < c["_from"]):
                    c["_from"] = entry["_from"]
                    c["from"] = entry["from"]
                if entry["_to"] and (not c["_to"] or entry["_to"] > c["_to"]):
                    c["_to"] = entry["_to"]
                    c["to"] = entry["to"]
                # keep a representative description (longest seen)
                if len(entry["description"]) > len(c["description"]):
                    c["description"] = entry["description"]
                merged = True
                break
        if not merged:
            clusters.append(
                {
                    "_customer_norm": c_norm,
                    "_from": entry["_from"],
                    "_to": entry["_to"],
                    "customer": entry["customer"],
                    "industry": entry["industry"],
                    "description": entry["description"],
                    "from": entry["from"],
                    "to": entry["to"],
                    "consultants": [entry["consultant"]],
                    "roles": set(entry["roles_set"]),
                    "skills": set(entry["skills_set"]),
                }
            )

    # Finalize: drop internal keys + lists-only
    out: list[dict[str, Any]] = []
    for c in clusters:
        out.append(
            {
                "customer": c["customer"],
                "industry": c["industry"],
                "description": c["description"],
                "from": c["from"],
                "to": c["to"],
                "roles": sorted(c["roles"]),
                "skills_used": sorted(c["skills"]),
                "consultants": c["consultants"],
            }
        )
    # Sort: most recent first by _to, then _from
    out.sort(
        key=lambda x: (
            x.get("to") or "",
            x.get("from") or "",
        ),
        reverse=True,
    )
    return out


def _fmt_ym(ym: tuple[int, int] | None) -> str:
    if not ym:
        return ""
    return f"{ym[0]:04d}-{ym[1]:02d}"


async def find_projects_aggregated(
    client: FlowcaseClient,
    *,
    industries: list[str] | None = None,
    customers: list[str] | None = None,
    skills: list[str] | None = None,
    description_contains: str | None = None,
    since_year: int | None = None,
    max_results: int = 20,
    max_candidates: int = MAX_CANDIDATE_CVS,
    lang: str = "no",
) -> dict[str, Any]:
    """Find delivery-like clusters of project experiences matching filters."""

    industry_names, unres_industries = await _resolve_industry_names(
        client, industries, lang
    )
    customer_names, unres_customers = await _resolve_customer_names(
        client, customers, lang
    )
    skill_ids, skill_names, unres_skills = await _resolve_skill_names_and_ids(
        client, skills, lang
    )

    # Candidate selection via data_export/users
    all_users = await client.get_all_users_via_data_export()

    # Translate taxonomy names back to their raw IDs for scoring
    industries_cat = await client.get_industries() if industry_names else []
    industry_ids_from_names: set[str] = set()
    for item in industries_cat:
        name_norm = _normalize_customer(_data_export_name(item, lang))
        if name_norm in industry_names:
            iid = item.get("id") or item.get("_id")
            if iid:
                industry_ids_from_names.add(iid)

    customers_cat = await client.get_customers() if customer_names else []
    customer_ids_from_names: set[str] = set()
    for item in customers_cat:
        name_norm = _normalize_customer(_data_export_name(item, lang))
        if name_norm in customer_names:
            cid = item.get("id") or item.get("_id")
            if cid:
                customer_ids_from_names.add(cid)

    # Score + pick top N candidates
    scored: list[tuple[int, dict[str, Any]]] = []
    any_filter = bool(
        industry_ids_from_names or customer_ids_from_names or skill_ids
    )
    for user in all_users:
        if user.get("deactivated"):
            continue
        if any_filter:
            score = _candidate_score(
                user,
                industry_ids_from_names,
                customer_ids_from_names,
                skill_ids,
            )
            if score <= 0:
                continue
        else:
            score = 1
        scored.append((score, user))
    scored.sort(key=lambda t: -t[0])
    candidates = [u for _, u in scored[:max_candidates]]

    logger.info(
        "find_projects: %d candidates out of %d users "
        "(filters industries=%d customers=%d skills=%d)",
        len(candidates),
        len(all_users),
        len(industry_ids_from_names),
        len(customer_ids_from_names),
        len(skill_ids),
    )

    # Fetch CVs in parallel (bounded)
    sem = asyncio.Semaphore(PARALLEL_CV_FETCHES)

    async def fetch_one(u: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
        uid = u.get("id") or u.get("_id")
        cid = u.get("cv_id")
        if not uid or not cid:
            return u, None
        async with sem:
            try:
                cv = await client.get_cv(uid, cid)
            except Exception:
                logger.exception("get_cv failed for %s", uid)
                return u, None
        return u, cv

    fetched = await asyncio.gather(*[fetch_one(u) for u in candidates])

    # Extract matching project_experiences
    raw: list[dict[str, Any]] = []
    for user, cv in fetched:
        if not cv:
            continue
        for proj in cv.get("project_experiences") or []:
            if proj.get("disabled"):
                continue
            if not _project_matches_filters(
                proj,
                industry_ids=industry_names if industry_names else None,
                customer_names_norm=customer_names,
                skill_ids=skill_names if skill_names else None,
                description_contains=description_contains,
                since_year=since_year,
                lang=lang,
            ):
                continue
            customer_display = pick_lang(proj.get("customer"), lang) or "(ukjent kunde)"
            industry_display = pick_lang(proj.get("industry"), lang)
            description = (
                pick_lang(proj.get("description"), lang)
                or pick_lang(proj.get("long_description"), lang)
                or ""
            )
            yf = _yearmonth(proj.get("year_from"), proj.get("month_from"))
            yt = _yearmonth(proj.get("year_to"), proj.get("month_to"))
            roles = [
                pick_lang(r.get("long_description") or r.get("summary"), lang)
                for r in (proj.get("roles") or [])
                if isinstance(r, dict)
            ]
            roles = [r for r in roles if r]
            pes_skills = [
                pick_lang(s.get("tags"), lang)
                for s in (proj.get("project_experience_skills") or [])
                if isinstance(s, dict)
            ]
            pes_skills = [s for s in pes_skills if s]
            raw.append(
                {
                    "_customer_norm": _normalize_customer(customer_display),
                    "_from": yf,
                    "_to": yt,
                    "customer": customer_display,
                    "industry": industry_display,
                    "description": description,
                    "from": _fmt_ym(yf),
                    "to": _fmt_ym(yt),
                    "roles_set": set(roles),
                    "skills_set": set(pes_skills),
                    "consultant": {
                        "name": user.get("name"),
                        "user_id": user.get("id") or user.get("_id"),
                        "cv_id": user.get("cv_id"),
                        "email": user.get("email"),
                        "roles": roles,
                    },
                }
            )

    aggregated = _aggregate_projects(raw, lang)

    return {
        "filters": {
            "industries": industries or [],
            "customers": customers or [],
            "skills": skills or [],
            "description_contains": description_contains,
            "since_year": since_year,
        },
        "unresolved": {
            "industries": unres_industries,
            "customers": unres_customers,
            "skills": unres_skills,
        },
        "total": len(aggregated),
        "returned": min(len(aggregated), max_results),
        "candidates_scanned": len(candidates),
        "deliveries": aggregated[:max_results],
    }
