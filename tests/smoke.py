"""End-to-end smoke test of all Flowcase MCP tools against prod.

Exercises the 6 tools in the natural workflow order:
    list_offices -> search_users -> find_user -> get_cv
    list_skills  -> find_users_by_skill

Prints a compact line per step — no PII bodies, just counts and first IDs.
Run:  python tests/smoke.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

# Windows default is cp1252; force UTF-8 so Norwegian names etc. print cleanly.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

# Silence httpx INFO logs — one per page of bulk scans is way too noisy.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from flowcase_mcp.server import (
    FindUserInput,
    FindUsersBySkillInput,
    GetCvInput,
    ListOfficesInput,
    ListSkillsInput,
    ResponseFormat,
    SearchUsersInput,
    flowcase_find_user,
    flowcase_find_users_by_skill,
    flowcase_get_cv,
    flowcase_list_offices,
    flowcase_list_skills,
    flowcase_search_users,
)


def banner(label: str) -> None:
    print(f"\n=== {label} ===", flush=True)


def summarize_json(raw: str, *, keys_to_show: int = 10) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return f"(non-JSON, {len(raw)} chars) — first 200: {raw[:200]}"
    if isinstance(data, list):
        return f"list of {len(data)}"
    if isinstance(data, dict):
        shown = {}
        for k, v in list(data.items())[:keys_to_show]:
            if isinstance(v, list):
                shown[k] = f"list[{len(v)}]"
            elif isinstance(v, dict):
                shown[k] = f"dict[{len(v)} keys]"
            elif isinstance(v, str) and len(v) > 60:
                shown[k] = v[:60] + "..."
            else:
                shown[k] = v
        return json.dumps(shown, ensure_ascii=False)
    return f"{type(data).__name__}: {str(data)[:200]}"


async def main() -> int:
    # -- 1. list_offices (NO only) ------------------------------------------
    banner("1. flowcase_list_offices(country_codes=['no'], json)")
    out = await flowcase_list_offices(
        ListOfficesInput(country_codes=["no"], response_format=ResponseFormat.JSON)
    )
    data = json.loads(out)
    no_country = next((c for c in data if c.get("country_code") == "no"), None)
    if not no_country or not no_country.get("offices"):
        print("FAIL: no NO offices returned")
        return 1
    office_id = no_country["offices"][0]["office_id"]
    office_name = no_country["offices"][0]["office_name"]
    print(f"OK   -> {len(no_country['offices'])} NO offices; first: {office_name} ({office_id})")

    # -- 2. search_users in that office ------------------------------------
    banner(f"2. flowcase_search_users(office_ids=['{office_id[:8]}...'], size=3, json)")
    out = await flowcase_search_users(
        SearchUsersInput(
            office_ids=[office_id],
            size=3,
            response_format=ResponseFormat.JSON,
        )
    )
    data = json.loads(out)
    users = data.get("users") or []
    if not users:
        print("FAIL: no users returned from search")
        return 1
    sample_user = users[0]
    user_id = sample_user["user_id"]
    cv_id = sample_user["cv_id"]
    email = sample_user.get("email") or ""
    print(f"OK   -> {len(users)} users; first email: {email[:3]}***")
    print(f"       user_id={user_id}  cv_id={cv_id}")

    # -- 3. find_user by that user's email ---------------------------------
    if email:
        banner("3. flowcase_find_user(email=<first user's email>, json)")
        out = await flowcase_find_user(
            FindUserInput(email=email, response_format=ResponseFormat.JSON)
        )
        data = json.loads(out)
        print(f"OK   -> {summarize_json(out)}")
        if data.get("user_id") != user_id:
            print(
                f"WARN: find_user returned different user_id ({data.get('user_id')}) "
                f"than search_users ({user_id})"
            )
    else:
        print("SKIP (no email on sample user)")

    # -- 4. get_cv (compact, default sections) -----------------------------
    banner(f"4. flowcase_get_cv(user_id, cv_id) — compact default sections")
    out = await flowcase_get_cv(
        GetCvInput(
            user_id=user_id,
            cv_id=cv_id,
            response_format=ResponseFormat.JSON,
        )
    )
    try:
        cv = json.loads(out)
    except json.JSONDecodeError:
        print(f"FAIL: non-JSON CV response: {out[:200]}")
        return 1
    present_sections = [
        k
        for k in ("key_qualifications", "recent_projects", "technologies")
        if k in cv
    ]
    print(
        f"OK   -> markdown {len(out)} chars; sections present: {present_sections}; "
        f"{len(cv.get('technologies') or [])} tech categories"
    )

    # -- 5. list_skills with a query ---------------------------------------
    banner("5. flowcase_list_skills(query='azure', limit=5, json)")
    out = await flowcase_list_skills(
        ListSkillsInput(
            query="azure",
            limit=5,
            response_format=ResponseFormat.JSON,
        )
    )
    data = json.loads(out)
    skills = data.get("skills") or []
    print(
        f"OK   -> total {data.get('total')} skills matched; showing {len(skills)}: "
        f"{[s['name'] for s in skills[:5]]}"
    )
    if not skills:
        print("WARN: no azure skills — will fall back to 'office' for next test")
        probe = ListSkillsInput(
            query="office", limit=5, response_format=ResponseFormat.JSON
        )
        out = await flowcase_list_skills(probe)
        skills = json.loads(out).get("skills") or []

    if not skills:
        print("FAIL: no skills found for any probe query")
        return 1
    probe_skill_name = skills[0]["name"]

    # -- 6. find_users_by_skill (NO default scope) -------------------------
    banner(
        f"6. flowcase_find_users_by_skill(skills=['{probe_skill_name}']) "
        f"— default NO scope, max 5"
    )
    out = await flowcase_find_users_by_skill(
        FindUsersBySkillInput(
            skills=[probe_skill_name],
            max_results=5,
            response_format=ResponseFormat.JSON,
        )
    )
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        print(f"FAIL: tool returned non-JSON. First 500 chars:\n{out[:500]}")
        return 1
    print(
        f"OK   -> scope={data.get('scope')}  "
        f"total_matches={data.get('total_matches')}  "
        f"returned={data.get('returned')}  "
        f"resolved_ids={len(data.get('resolved_skill_ids') or [])}"
    )
    if data.get("users"):
        u = data["users"][0]
        print(
            f"       first match: {u.get('name')} "
            f"({len(u.get('matching_skills') or [])} matching skills)"
        )

    print("\nAll tools exercised successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
