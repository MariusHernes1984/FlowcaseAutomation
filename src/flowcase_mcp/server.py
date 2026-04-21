"""Flowcase MCP server — read-only MVP.

Exposes four tools against the Atea Flowcase ServiceHub proxy:

* ``flowcase_list_offices`` — countries and office IDs
* ``flowcase_search_users`` — list users within offices (by country or office IDs)
* ``flowcase_find_user`` — lookup by email or external_unique_id
* ``flowcase_get_cv`` — fetch a CV (compact-by-section by default, ``verbose=true`` for full)

Note: despite the name, ``/search`` on the Atea proxy does NOT support
text/skill filters. It is simply "list users within the given offices,
alphabetically by email". All observed filter params (``q``, ``must[]``,
``query``, ``search``) are silently ignored. Skill-based filtering must be
done client-side by iterating CVs, or asynchronously via ``/cv-report``.
"""

from __future__ import annotations

import json
import os
from enum import Enum
from typing import Any, Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, model_validator

from flowcase_mcp.client import FlowcaseClient, format_http_error
from flowcase_mcp.formatting import (
    DEFAULT_CV_SECTIONS,
    VALID_CV_SECTIONS,
    compact_cv,
    compact_user,
    pick_lang,
)

load_dotenv()

mcp = FastMCP("flowcase_mcp")
_client: FlowcaseClient | None = None


def _get_client() -> FlowcaseClient:
    global _client
    if _client is None:
        _client = FlowcaseClient.from_env()
    return _client


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


# ---------------------------------------------------------------------------
# flowcase_list_offices
# ---------------------------------------------------------------------------


class ListOfficesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    country_codes: Optional[list[str]] = Field(
        default=None,
        description=(
            "Optional filter — only return offices in these country codes "
            "(e.g. ['no','se']). Leave empty to return all countries."
        ),
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' for humans, 'json' for machine-readable output.",
    )


@mcp.tool(
    name="flowcase_list_offices",
    annotations={
        "title": "List Flowcase countries and offices",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def flowcase_list_offices(params: ListOfficesInput) -> str:
    """List countries and their offices, with IDs.

    Usually not required before searching — ``flowcase_search_users`` can
    resolve offices from country codes automatically. Use this tool when you
    need the explicit office IDs (for targeted multi-office search) or want
    to see how many users each office has.
    """
    try:
        countries = await _get_client().get_countries()
    except Exception as e:
        return f"Error: {format_http_error(e)}"

    filter_codes = (
        {c.lower() for c in params.country_codes} if params.country_codes else None
    )

    filtered = [
        c
        for c in countries
        if filter_codes is None or (c.get("code") or "").lower() in filter_codes
    ]

    if params.response_format == ResponseFormat.JSON:
        compact = [
            {
                "country_id": c.get("_id"),
                "country_code": c.get("code"),
                "offices": [
                    {
                        "office_id": o.get("_id"),
                        "office_name": o.get("name"),
                        "num_users": o.get("num_users"),
                    }
                    for o in (c.get("offices") or [])
                ],
            }
            for c in filtered
        ]
        return json.dumps(compact, indent=2, ensure_ascii=False)

    lines: list[str] = ["# Flowcase countries and offices", ""]
    for country in filtered:
        lines.append(
            f"## {country.get('code', '?')} "
            f"(country_id: `{country.get('_id')}`)"
        )
        for office in country.get("offices") or []:
            users = office.get("num_users")
            users_suffix = f" — {users} users" if users is not None else ""
            lines.append(
                f"- **{office.get('name', '?')}** "
                f"(office_id: `{office.get('_id')}`){users_suffix}"
            )
        lines.append("")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# flowcase_search_users
# ---------------------------------------------------------------------------


class SearchUsersInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    country_codes: Optional[list[str]] = Field(
        default=None,
        description=(
            "Country codes to scope the listing (e.g. ['no'] or ['no','se']). "
            "If omitted and no office_ids given, the server's default country "
            "(FLOWCASE_DEFAULT_COUNTRY) is used."
        ),
    )
    office_ids: Optional[list[str]] = Field(
        default=None,
        description=(
            "Explicit office IDs. Takes precedence over country_codes. "
            "Obtain via flowcase_list_offices if needed."
        ),
    )
    size: int = Field(
        default=20,
        description="Page size (1-100). Default 20.",
        ge=1,
        le=100,
    )
    from_offset: int = Field(
        default=0,
        description="Number of results to skip for pagination.",
        ge=0,
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="flowcase_search_users",
    annotations={
        "title": "List Flowcase users within offices or countries",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def flowcase_search_users(params: SearchUsersInput) -> str:
    """List users in one or more offices (alphabetical by email).

    Despite the underlying endpoint being named ``/search``, the Atea
    Flowcase proxy does NOT accept text or skill filters — this tool simply
    pages through users within the resolved offices. To filter by skill or
    name, fetch candidate users and then call ``flowcase_get_cv`` for each.

    Each returned record includes ``user_id`` and ``cv_id`` (default_cv_id),
    ready for direct use with ``flowcase_get_cv``.
    """
    client = _get_client()
    try:
        office_ids = await client.resolve_office_ids(
            office_ids=params.office_ids,
            country_codes=params.country_codes,
        )
    except Exception as e:
        return f"Error: {format_http_error(e)}"

    query_params: list[tuple[str, Any]] = [
        ("office_ids[]", office_id) for office_id in office_ids
    ]
    query_params.append(("size", params.size))
    query_params.append(("from", params.from_offset))

    try:
        data = await client.get("/search", params=query_params)
    except Exception as e:
        return f"Error: {format_http_error(e)}"

    records = data if isinstance(data, list) else []
    lang = os.environ.get("FLOWCASE_DEFAULT_LANGUAGE", "no")

    items = [
        {
            "user_id": r.get("user_id") or r.get("_id"),
            "cv_id": r.get("default_cv_id"),
            "name": r.get("name"),
            "title": pick_lang(r.get("title"), lang),
            "email": r.get("email"),
            "external_unique_id": r.get("external_unique_id"),
            "office_name": r.get("office_name"),
            "country_code": r.get("country_code"),
            "deactivated": r.get("deactivated"),
            "updated_at": r.get("updated_at"),
        }
        for r in records
    ]

    # The proxy gives no total count. If the page is full, more likely exist.
    has_more = len(items) >= params.size
    next_from = params.from_offset + len(items) if has_more else None

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "count": len(items),
                "from": params.from_offset,
                "size": params.size,
                "office_ids_resolved": office_ids,
                "has_more": has_more,
                "next_from": next_from,
                "users": items,
            },
            indent=2,
            ensure_ascii=False,
        )

    scope = (
        f"{len(office_ids)} office(s)"
        if params.office_ids
        else f"country {params.country_codes or [client.default_country]}"
    )
    lines: list[str] = [
        f"# Users in {scope}",
        f"_Showing {len(items)} result(s) from offset {params.from_offset}._",
        "",
    ]
    for it in items:
        header = f"## {it['name'] or '(unnamed)'}"
        if it.get("title"):
            header += f" — {it['title']}"
        lines.append(header)
        lines.append(f"- user_id: `{it['user_id']}`")
        lines.append(f"- cv_id: `{it['cv_id']}`")
        if it.get("email"):
            lines.append(f"- Email: {it['email']}")
        if it.get("office_name"):
            lines.append(
                f"- Office: {it['office_name']} ({it.get('country_code') or '-'})"
            )
        if it.get("deactivated"):
            lines.append("- **Deactivated**")
        lines.append("")
    if has_more:
        lines.append(
            f"_More available — call again with from_offset={next_from}._"
        )
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# flowcase_find_user
# ---------------------------------------------------------------------------


class FindUserInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    email: Optional[str] = Field(
        default=None, description="Email of the user to look up."
    )
    external_unique_id: Optional[str] = Field(
        default=None,
        description="ATEA domain username (external_unique_id) of the user.",
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)

    @model_validator(mode="after")
    def _require_one_identifier(self) -> "FindUserInput":
        if not self.email and not self.external_unique_id:
            raise ValueError("Provide either 'email' or 'external_unique_id'.")
        return self


@mcp.tool(
    name="flowcase_find_user",
    annotations={
        "title": "Find a Flowcase user by email or domain username",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def flowcase_find_user(params: FindUserInput) -> str:
    """Find a single user by email or Atea domain username.

    Returns identity details including ``user_id`` and ``default_cv_id``,
    which together can be passed to ``flowcase_get_cv`` to fetch the CV.
    """
    query: dict[str, Any] = {}
    if params.email:
        query["email"] = params.email
    if params.external_unique_id:
        query["external_unique_id"] = params.external_unique_id

    try:
        data = await _get_client().get("/users/find", params=query)
    except Exception as e:
        return f"Error: {format_http_error(e)}"

    record = data[0] if isinstance(data, list) and data else data
    if not record:
        return "No user found for the given identifier."

    lang = os.environ.get("FLOWCASE_DEFAULT_LANGUAGE", "no")
    compact = compact_user(record, lang=lang)

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(compact, indent=2, ensure_ascii=False)

    lines = [
        f"# {compact.get('name') or '(unnamed)'}",
    ]
    if compact.get("title"):
        lines.append(f"_{compact['title']}_")
    lines.extend(
        [
            "",
            f"- user_id: `{compact.get('user_id')}`",
            f"- default_cv_id: `{compact.get('default_cv_id')}`",
            f"- Email: {compact.get('email') or '-'}",
            f"- External ID: {compact.get('external_unique_id') or '-'}",
            f"- Role: {compact.get('role') or '-'}",
            f"- Office: {compact.get('office_name') or '-'} "
            f"({compact.get('country_code') or '-'})",
            f"- Updated: {compact.get('updated_at') or '-'}",
        ]
    )
    if compact.get("deactivated"):
        lines.append("- **Deactivated**")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# flowcase_get_cv
# ---------------------------------------------------------------------------


class GetCvInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    user_id: str = Field(..., description="Flowcase user_id.", min_length=1)
    cv_id: str = Field(
        ...,
        description="Flowcase CV id (usually default_cv_id from user lookup).",
        min_length=1,
    )
    sections: Optional[list[str]] = Field(
        default=None,
        description=(
            "Optional CV sections to include. Default is "
            f"{list(DEFAULT_CV_SECTIONS)}. Valid: "
            f"{sorted(VALID_CV_SECTIONS)} plus 'all'. "
            "Identity (name, title, email, phone, etc.) is always included. "
            "Unknown names are silently ignored."
        ),
    )
    limit_projects: int = Field(
        default=5,
        description="Max number of recent projects when 'projects' is in sections.",
        ge=1,
        le=50,
    )
    language: str = Field(
        default_factory=lambda: os.environ.get("FLOWCASE_DEFAULT_LANGUAGE", "no"),
        description="Preferred language for multilingual fields (no, se, dk, int, en).",
    )
    verbose: bool = Field(
        default=False,
        description=(
            "If true, return the full raw CV JSON (large). Default is a "
            "compact summary optimized for LLM context."
        ),
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="flowcase_get_cv",
    annotations={
        "title": "Get a Flowcase CV",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def flowcase_get_cv(params: GetCvInput) -> str:
    """Fetch a user's CV.

    Full payloads from Flowcase can exceed 50 KB. By default this tool
    returns a compact summary restricted to the sections in
    ``DEFAULT_CV_SECTIONS`` — identity, key qualifications, projects, and
    skills. Use ``sections=["all"]`` to include everything, or pass a
    specific list to drill into e.g. certifications without the rest.

    CVs contain personal data (names, emails, histories). Handle downstream
    carefully.
    """
    try:
        cv = await _get_client().get(f"/cvs/{params.user_id}/{params.cv_id}")
    except Exception as e:
        return f"Error: {format_http_error(e)}"

    if params.verbose:
        return json.dumps(cv, indent=2, ensure_ascii=False)

    summary = compact_cv(
        cv,
        lang=params.language,
        sections=params.sections,
        limit_projects=params.limit_projects,
    )

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(summary, indent=2, ensure_ascii=False)

    return _format_cv_markdown(summary)


def _format_cv_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = [f"# {summary.get('name') or '(unnamed)'}"]
    if summary.get("title"):
        lines.append(f"_{summary['title']}_")
    lines.append("")

    meta = []
    for label, key in [
        ("Email", "email"),
        ("Phone", "telephone"),
        ("Location", "place_of_residence"),
        ("Language", "language_code"),
        ("Updated", "updated_at"),
    ]:
        value = summary.get(key)
        if value:
            meta.append(f"- **{label}**: {value}")
    if meta:
        lines.extend(meta)
        lines.append("")

    if "key_qualifications" in summary and summary["key_qualifications"]:
        lines.append("## Key qualifications")
        for kq in summary["key_qualifications"]:
            label = kq.get("label")
            desc = kq.get("summary")
            if label and desc:
                lines.append(f"- **{label}**: {desc}")
            elif label:
                lines.append(f"- **{label}**")
            elif desc:
                lines.append(f"- {desc}")
        lines.append("")

    if "technologies" in summary and summary["technologies"]:
        lines.append("## Technologies")
        for tech in summary["technologies"]:
            cat = tech.get("category") or "(uncategorized)"
            skills = ", ".join(tech.get("skills") or [])
            lines.append(f"- **{cat}**: {skills}")
        lines.append("")

    if "recent_projects" in summary and summary["recent_projects"]:
        lines.append("## Recent projects")
        for project in summary["recent_projects"]:
            header_parts = [project.get("customer") or "(customer)"]
            dates = f"{project.get('from', '')}–{project.get('to', '')}".strip("–")
            if dates:
                header_parts.append(dates)
            lines.append(f"### {' | '.join(header_parts)}")
            if project.get("industry"):
                lines.append(f"- Industry: {project['industry']}")
            if project.get("description"):
                lines.append(f"- {project['description']}")
            if project.get("roles"):
                lines.append(f"- Roles: {'; '.join(project['roles'])}")
            if project.get("skills"):
                lines.append(f"- Skills: {', '.join(project['skills'])}")
            lines.append("")

    if "certifications" in summary and summary["certifications"]:
        lines.append("## Certifications")
        for cert in summary["certifications"]:
            parts = [
                p
                for p in [cert.get("name"), cert.get("organiser"), cert.get("year")]
                if p
            ]
            lines.append(f"- {' — '.join(parts)}" if parts else "- (unnamed)")
        lines.append("")

    if "languages" in summary and summary["languages"]:
        lines.append("## Languages")
        for lang_entry in summary["languages"]:
            lines.append(
                f"- {lang_entry.get('name') or ''}: {lang_entry.get('level') or ''}"
            )
        lines.append("")

    if "educations" in summary and summary["educations"]:
        lines.append("## Education")
        for edu in summary["educations"]:
            fr = edu.get("from") or ""
            to = edu.get("to") or ""
            dates = f"{fr}–{to}".strip("–")
            line = f"- {edu.get('degree') or ''} @ {edu.get('school') or ''}"
            if dates:
                line += f" ({dates})"
            lines.append(line.strip())
        lines.append("")

    if "work_experiences" in summary and summary["work_experiences"]:
        lines.append("## Work experience")
        for work in summary["work_experiences"]:
            year = work.get("from_year") or ""
            employer = work.get("employer") or ""
            desc = work.get("description") or ""
            line = f"- **{employer}** (from {year})" if year else f"- **{employer}**"
            if desc:
                line += f" — {desc}"
            lines.append(line)
        lines.append("")

    if "courses" in summary and summary["courses"]:
        lines.append("## Courses")
        for course in summary["courses"]:
            year = course.get("year") or ""
            line = f"- {course.get('name') or ''}"
            if year:
                line += f" ({year})"
            lines.append(line)
        lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# flowcase_list_skills
# ---------------------------------------------------------------------------


class ListSkillsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: Optional[str] = Field(
        default=None,
        description=(
            "Optional substring to filter skill names (case-insensitive, "
            "matches any language variant). E.g. 'python' matches 'Python', "
            "'Python 3', 'IronPython'."
        ),
    )
    limit: int = Field(
        default=50,
        description="Maximum number of skills to return.",
        ge=1,
        le=500,
    )
    offset: int = Field(
        default=0,
        description="Number of skills to skip (applies after filtering).",
        ge=0,
    )
    language: str = Field(
        default_factory=lambda: os.environ.get("FLOWCASE_DEFAULT_LANGUAGE", "no"),
        description="Preferred language for skill names (no, se, dk, int, en).",
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="flowcase_list_skills",
    annotations={
        "title": "List Flowcase skill taxonomy",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def flowcase_list_skills(params: ListSkillsInput) -> str:
    """Browse the approved skill taxonomy.

    Returns a list of ``{skill_id, name}`` pairs. Use ``query`` to narrow
    down by substring when searching for a specific technology or tool.
    Skill IDs returned here can be passed directly to
    ``flowcase_find_users_by_skill``.
    """
    client = _get_client()
    try:
        taxonomy = await client.get_skill_taxonomy()
    except Exception as e:
        return f"Error: {format_http_error(e)}"

    query = (params.query or "").strip().lower()

    items: list[dict[str, Any]] = []
    for skill in taxonomy:
        name = pick_lang(skill.get("values"), params.language)
        if not name:
            continue
        if query and query not in name.lower():
            # Also check all language variants to be permissive
            all_labels = skill.get("values") or {}
            matched = False
            if isinstance(all_labels, dict):
                for label in all_labels.values():
                    if isinstance(label, str) and query in label.lower():
                        matched = True
                        break
            if not matched:
                continue
        items.append(
            {
                "skill_id": skill.get("_id"),
                "name": name,
                "category_ids": skill.get("category_ids") or [],
            }
        )

    total = len(items)
    items.sort(key=lambda x: (x["name"] or "").lower())
    page = items[params.offset : params.offset + params.limit]
    has_more = (params.offset + len(page)) < total

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "total": total,
                "count": len(page),
                "offset": params.offset,
                "limit": params.limit,
                "has_more": has_more,
                "next_offset": params.offset + len(page) if has_more else None,
                "skills": page,
            },
            indent=2,
            ensure_ascii=False,
        )

    header = f"# Skills ({len(page)} of {total}"
    if query:
        header += f", filter '{params.query}'"
    header += ")"
    lines = [header, ""]
    for s in page:
        lines.append(f"- **{s['name']}** — `{s['skill_id']}`")
    if has_more:
        lines.append("")
        lines.append(
            f"_More available — call again with offset="
            f"{params.offset + len(page)}._"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# flowcase_find_users_by_skill
# ---------------------------------------------------------------------------


class FindUsersBySkillInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    skills: list[str] = Field(
        ...,
        description=(
            "Skill names or IDs to match (ANY-of logic — a user with any of "
            "the listed skills counts as a hit). Names are matched as "
            "case-insensitive substrings across all language variants, so "
            "'python' matches 'Python 2', 'Python 3', etc. 24-char hex "
            "strings are treated as raw skill IDs."
        ),
        min_length=1,
    )
    country_codes: Optional[list[str]] = Field(
        default=None,
        description=(
            "Country codes to scope results (default: server's "
            "FLOWCASE_DEFAULT_COUNTRY). Pass ['all'] or explicit office_ids "
            "to broaden."
        ),
    )
    office_ids: Optional[list[str]] = Field(
        default=None,
        description="Explicit office IDs. Takes precedence over country_codes.",
    )
    all_countries: bool = Field(
        default=False,
        description=(
            "If true, skip country/office scoping and search all users "
            "globally. Overrides country_codes and office_ids."
        ),
    )
    max_results: int = Field(
        default=50,
        description="Maximum number of matching users to return.",
        ge=1,
        le=500,
    )
    include_deactivated: bool = Field(
        default=False,
        description="If true, include users marked deactivated in Flowcase.",
    )
    language: str = Field(
        default_factory=lambda: os.environ.get("FLOWCASE_DEFAULT_LANGUAGE", "no"),
        description="Language for skill name resolution and display.",
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


@mcp.tool(
    name="flowcase_find_users_by_skill",
    annotations={
        "title": "Find Flowcase users by skill",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def flowcase_find_users_by_skill(params: FindUsersBySkillInput) -> str:
    """Find consultants who have any of the given skills.

    Under the hood this tool combines two data sources because the Flowcase
    proxy's ``/search`` endpoint does NOT support skill filters:

    * ``/masterdata/technologies/tags`` — skill name → ID resolution (cached)
    * ``/data_export/users`` — full user roster with skill IDs (cached 10 min)
    * ``/search`` — to resolve which users are in the target country's offices

    For country-scoped queries, the tool intersects the skill matches from
    ``/data_export/users`` with the user-ID set from ``/search``. Default
    scope is the server's configured country.

    The output is a compact list suitable for follow-up calls to
    ``flowcase_get_cv``.
    """
    client = _get_client()

    try:
        resolved_skill_ids, unresolved = await client.resolve_skill_identifiers(
            params.skills, lang=params.language
        )
    except Exception as e:
        return f"Error: {format_http_error(e)}"

    if not resolved_skill_ids:
        return (
            "No skills matched your input. Browse the taxonomy via "
            f"flowcase_list_skills to find the right spelling. "
            f"Unresolved: {params.skills}"
        )

    skill_id_set = set(resolved_skill_ids)

    # Build a lookup for skill names so we can show which skill matched.
    try:
        taxonomy = await client.get_skill_taxonomy()
    except Exception as e:
        return f"Error: {format_http_error(e)}"

    skill_name_by_id: dict[str, str] = {}
    for skill in taxonomy:
        sid = skill.get("_id")
        if not sid:
            continue
        skill_name_by_id[sid] = pick_lang(skill.get("values"), params.language) or sid

    # Resolve office scope unless all_countries is set.
    office_user_ids: set[str] | None = None
    scope_label = "all countries"
    if not params.all_countries:
        try:
            office_ids = await client.resolve_office_ids(
                office_ids=params.office_ids,
                country_codes=params.country_codes,
            )
        except Exception as e:
            return f"Error: {format_http_error(e)}"
        try:
            office_user_ids = await client.get_user_ids_in_offices(office_ids)
        except Exception as e:
            return f"Error: {format_http_error(e)}"
        if params.office_ids:
            scope_label = f"{len(office_ids)} office(s)"
        else:
            scope_label = (
                f"country {params.country_codes or [client.default_country]}"
            )

    # Scan data_export users and match.
    try:
        all_users = await client.get_all_users_via_data_export()
    except Exception as e:
        return f"Error: {format_http_error(e)}"

    matches: list[dict[str, Any]] = []
    for user in all_users:
        if user.get("deactivated") and not params.include_deactivated:
            continue
        user_skills = set(user.get("skills") or [])
        matching_ids = user_skills & skill_id_set
        if not matching_ids:
            continue
        uid = user.get("id")
        if office_user_ids is not None and uid not in office_user_ids:
            continue
        matches.append(
            {
                "user_id": uid,
                "cv_id": user.get("cv_id"),
                "name": user.get("name"),
                "email": user.get("email"),
                "matching_skills": sorted(
                    skill_name_by_id.get(sid, sid) for sid in matching_ids
                ),
                "matching_skill_ids": sorted(matching_ids),
                "total_skills": len(user_skills),
                "deactivated": user.get("deactivated"),
            }
        )

    # Order: most matches first, then by total skills desc.
    matches.sort(
        key=lambda m: (-len(m["matching_skills"]), -m["total_skills"], (m.get("name") or "").lower())
    )
    truncated = matches[: params.max_results]

    if params.response_format == ResponseFormat.JSON:
        return json.dumps(
            {
                "scope": scope_label,
                "requested_skills": params.skills,
                "resolved_skill_ids": resolved_skill_ids,
                "unresolved_inputs": unresolved,
                "total_matches": len(matches),
                "returned": len(truncated),
                "users": truncated,
            },
            indent=2,
            ensure_ascii=False,
        )

    # Markdown
    resolved_names = sorted(
        {skill_name_by_id.get(sid, sid) for sid in resolved_skill_ids}
    )
    lines: list[str] = [
        f"# Skill search — scope: {scope_label}",
        "",
        f"- Requested: {', '.join(params.skills)}",
        f"- Resolved to {len(resolved_skill_ids)} skill(s): "
        f"{', '.join(resolved_names[:10])}"
        + (" …" if len(resolved_names) > 10 else ""),
    ]
    if unresolved:
        lines.append(f"- **Unresolved inputs**: {unresolved}")
    lines.append(
        f"- **{len(matches)} matching users** "
        f"(showing {len(truncated)})"
    )
    lines.append("")

    for m in truncated:
        header = f"## {m.get('name') or '(unnamed)'}"
        if m.get("deactivated"):
            header += " (deactivated)"
        lines.append(header)
        lines.append(f"- user_id: `{m.get('user_id')}`")
        lines.append(f"- cv_id: `{m.get('cv_id')}`")
        if m.get("email"):
            lines.append(f"- Email: {m['email']}")
        lines.append(
            f"- Matching skills ({len(m['matching_skills'])}): "
            f"{', '.join(m['matching_skills'])}"
        )
        lines.append(f"- Total skills on CV: {m['total_skills']}")
        lines.append("")

    if len(matches) > len(truncated):
        lines.append(
            f"_{len(matches) - len(truncated)} more match(es). "
            f"Increase max_results or narrow skills._"
        )
    return "\n".join(lines).strip()
