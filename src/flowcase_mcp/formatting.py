"""Helpers for multilingual value extraction and CV compaction.

Flowcase stores localized strings as dicts like
``{"dk": "...", "int": "...", "no": "...", "se": "..."}`` where ``int``
is the international/English variant. Many CV fields are nested lists of
such records, and the raw CV payload can easily exceed 50 KB. These helpers
produce a compact summary suitable for LLM context windows.
"""

from __future__ import annotations

from typing import Any, Iterable

LANGUAGE_FALLBACK_ORDER = ["no", "int", "en", "se", "dk"]

VALID_CV_SECTIONS: set[str] = {
    "qualifications",
    "projects",
    "skills",
    "certifications",
    "languages",
    "educations",
    "work_experiences",
    "courses",
}
DEFAULT_CV_SECTIONS: tuple[str, ...] = ("qualifications", "projects", "skills")


def pick_lang(value: Any, preferred: str = "no") -> str:
    """Pick a single string from a multilingual value dict.

    Falls back through ``preferred`` → ``no`` → ``int`` → ``en`` → ``se`` →
    ``dk`` → any non-empty value. Returns ``""`` if nothing usable is found.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return str(value)
    chain = [preferred] + [c for c in LANGUAGE_FALLBACK_ORDER if c != preferred]
    for code in chain:
        text = value.get(code)
        if isinstance(text, str) and text.strip():
            return text
    for text in value.values():
        if isinstance(text, str) and text.strip():
            return text
    return ""


def compact_user(user: dict[str, Any], *, lang: str = "no") -> dict[str, Any]:
    """Return a compact subset of a user record for LLM consumption."""
    return {
        "user_id": user.get("user_id") or user.get("_id"),
        "default_cv_id": user.get("default_cv_id"),
        "name": user.get("name"),
        "title": pick_lang(user.get("title"), lang),
        "email": user.get("email"),
        "external_unique_id": user.get("external_unique_id"),
        "role": user.get("role"),
        "office_id": user.get("office_id"),
        "office_name": user.get("office_name"),
        "country_code": user.get("country_code"),
        "deactivated": user.get("deactivated"),
        "updated_at": user.get("updated_at"),
    }


def normalize_sections(sections: Iterable[str] | None) -> set[str]:
    """Normalize a list of CV section names.

    - ``None`` or empty → default sections
    - ``"all"`` → every valid section
    - Unknown section names are silently ignored
    """
    if not sections:
        return set(DEFAULT_CV_SECTIONS)
    requested = {s.strip().lower() for s in sections if isinstance(s, str) and s.strip()}
    if not requested:
        return set(DEFAULT_CV_SECTIONS)
    if "all" in requested:
        return set(VALID_CV_SECTIONS)
    return requested & VALID_CV_SECTIONS


def _date_range_from(year: Any, month: Any) -> str:
    return "-".join(str(p) for p in (year, month) if p)


def compact_cv(
    cv: dict[str, Any],
    *,
    lang: str = "no",
    sections: Iterable[str] | None = None,
    limit_projects: int = 5,
) -> dict[str, Any]:
    """Summarize a full CV into a compact dict.

    Identity (name, title, email, phone, location, language, updated_at)
    is always included. Optional sections are controlled by ``sections``:

    - ``qualifications``  — key_qualifications list
    - ``projects``        — ``limit_projects`` most recent projects
    - ``skills``          — technologies grouped by category
    - ``certifications``  — certifications list
    - ``languages``       — language proficiencies
    - ``educations``      — education history
    - ``work_experiences`` — work history outside projects
    - ``courses``         — training courses

    Passing ``sections=["all"]`` includes everything. Unknown section names
    are silently ignored.
    """

    def ml(value: Any) -> str:
        return pick_lang(value, lang)

    selected = normalize_sections(sections)

    out: dict[str, Any] = {
        "user_id": cv.get("user_id"),
        "cv_id": cv.get("_id"),
        "name": cv.get("name") or cv.get("navn"),
        "title": ml(cv.get("title")),
        "email": cv.get("email"),
        "telephone": cv.get("telephone") or cv.get("telefon"),
        "place_of_residence": ml(cv.get("place_of_residence")),
        "language_code": cv.get("language_code"),
        "updated_at": cv.get("updated_at"),
    }

    if "qualifications" in selected:
        quals = [
            {"label": ml(kq.get("label")), "summary": ml(kq.get("long_description"))}
            for kq in (cv.get("key_qualifications") or [])
            if not kq.get("disabled")
        ]
        out["key_qualifications"] = [q for q in quals if q["label"] or q["summary"]]

    if "projects" in selected:
        projects_sorted = sorted(
            cv.get("project_experiences") or [],
            key=lambda p: (p.get("year_from") or "", p.get("month_from") or ""),
            reverse=True,
        )
        recent: list[dict[str, Any]] = []
        for p in projects_sorted:
            if p.get("disabled"):
                continue
            roles = [
                ml(r.get("long_description") or r.get("summary"))
                for r in (p.get("roles") or [])
            ]
            skills = [
                ml(s.get("tags"))
                for s in (p.get("project_experience_skills") or [])
            ]
            recent.append(
                {
                    "customer": ml(p.get("customer")),
                    "industry": ml(p.get("industry")),
                    "from": _date_range_from(p.get("year_from"), p.get("month_from")),
                    "to": _date_range_from(p.get("year_to"), p.get("month_to")),
                    "description": ml(p.get("description")),
                    "roles": [r for r in roles if r],
                    "skills": [s for s in skills if s][:20],
                }
            )
            if len(recent) >= limit_projects:
                break
        out["recent_projects"] = recent

    if "skills" in selected:
        technologies: list[dict[str, Any]] = []
        for tech in cv.get("technologies") or []:
            if tech.get("disabled"):
                continue
            tech_skills = [
                ml(s.get("tags"))
                for s in (tech.get("technology_skills") or [])
                if ml(s.get("tags"))
            ]
            if tech_skills:
                technologies.append(
                    {"category": ml(tech.get("category")), "skills": tech_skills}
                )
        out["technologies"] = technologies

    if "certifications" in selected:
        out["certifications"] = [
            {
                "name": ml(c.get("name")),
                "organiser": ml(c.get("organiser")),
                "year": c.get("year"),
                "month": c.get("month"),
            }
            for c in (cv.get("certifications") or [])
            if not c.get("disabled")
        ]

    if "languages" in selected:
        out["languages"] = [
            {"name": ml(entry.get("name")), "level": ml(entry.get("level"))}
            for entry in (cv.get("languages") or [])
            if not entry.get("disabled")
        ]

    if "educations" in selected:
        out["educations"] = [
            {
                "degree": ml(e.get("degree")),
                "school": ml(e.get("school")),
                "from": e.get("year_from"),
                "to": e.get("year_to"),
            }
            for e in (cv.get("educations") or [])
            if not e.get("disabled")
        ]

    if "work_experiences" in selected:
        out["work_experiences"] = [
            {
                "employer": ml(w.get("employer")),
                "description": ml(w.get("description")),
                "from_year": w.get("year_from"),
                "from_month": w.get("month_from"),
            }
            for w in (cv.get("work_experiences") or [])
            if not w.get("disabled")
        ]

    if "courses" in selected:
        out["courses"] = [
            {
                "name": ml(c.get("name")),
                "year": c.get("year"),
                "month": c.get("month"),
            }
            for c in (cv.get("courses") or [])
            if not c.get("disabled")
        ]

    return out
