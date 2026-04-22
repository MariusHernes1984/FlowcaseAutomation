"""Async HTTP client for the Flowcase ServiceHub proxy."""

from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://servicehub.atea.com/flowcase"
DEFAULT_API_KEY_HEADER = "Ocp-Apim-Subscription-Key"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_COUNTRY = "no"

COUNTRIES_CACHE_TTL = 3600.0   # 1 hour — countries/offices change rarely
SKILLS_CACHE_TTL = 3600.0      # 1 hour — skill taxonomy changes rarely
DATA_EXPORT_CACHE_TTL = 600.0  # 10 minutes — CVs can update during a session
BULK_SCAN_PAGE_DELAY = 0.05    # Delay between paginated pages — just enough to be polite
MAX_RETRIES = 5                # Retry attempts on 429/timeouts
INITIAL_BACKOFF = 2.0          # Seconds for first retry; doubles each attempt
MAX_RETRY_AFTER_SECONDS = 30.0 # Cap honoring the server's Retry-After header

OBJECT_ID_RE = re.compile(r"^[0-9a-f]{24}$", re.IGNORECASE)


class FlowcaseConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


class FlowcaseClient:
    """Async client for the Flowcase proxy API.

    Authentication is a single HTTP header (default
    ``Ocp-Apim-Subscription-Key`` for Atea ServiceHub / Azure APIM).

    The client keeps an in-memory cache of semi-static data
    (``/countries``, skill taxonomy, ``/data_export/users`` bulk scan)
    to support affordable skill search. Bulk scans retry on HTTP 429
    with exponential backoff.
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key_header: str = DEFAULT_API_KEY_HEADER,
        default_country: str = DEFAULT_COUNTRY,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not api_key:
            raise FlowcaseConfigError(
                "FLOWCASE_API_KEY is not set. Copy .env.example to .env and "
                "paste your Atea ServiceHub subscription key."
            )
        self._base_url = base_url.rstrip("/")
        self._headers = {api_key_header: api_key, "Accept": "application/json"}
        self._timeout = timeout
        self._default_country = default_country.lower()

        self._countries_cache: tuple[list[dict[str, Any]], float] | None = None
        self._skills_cache: tuple[list[dict[str, Any]], float] | None = None
        self._data_export_users_cache: tuple[list[dict[str, Any]], float] | None = None

    @classmethod
    def from_env(cls) -> "FlowcaseClient":
        return cls(
            api_key=os.environ.get("FLOWCASE_API_KEY", ""),
            base_url=os.environ.get("FLOWCASE_BASE_URL", DEFAULT_BASE_URL),
            api_key_header=os.environ.get(
                "FLOWCASE_API_KEY_HEADER", DEFAULT_API_KEY_HEADER
            ),
            default_country=os.environ.get("FLOWCASE_DEFAULT_COUNTRY", DEFAULT_COUNTRY),
        )

    @property
    def default_country(self) -> str:
        return self._default_country

    async def get(
        self,
        path: str,
        params: dict[str, Any] | list[tuple[str, Any]] | None = None,
        *,
        max_retries: int = MAX_RETRIES,
    ) -> Any:
        """GET with retry on HTTP 429 (rate limit) and timeouts."""
        url = f"{self._base_url}{path}"
        backoff = INITIAL_BACKOFF
        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(
                        url, headers=self._headers, params=params
                    )
                    if response.status_code == 429 and attempt < max_retries:
                        retry_after = response.headers.get("Retry-After")
                        wait_s = float(retry_after) if retry_after else backoff
                        await asyncio.sleep(min(wait_s, MAX_RETRY_AFTER_SECONDS))
                        backoff *= 2
                        continue
                    response.raise_for_status()
                    return response.json()
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt >= max_retries:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2
        if last_exc:
            raise last_exc
        return None

    # ------------------------------------------------------------------
    # /countries caching + office resolution
    # ------------------------------------------------------------------

    async def get_countries(self, *, force_refresh: bool = False) -> list[dict[str, Any]]:
        now = time.time()
        if not force_refresh and self._countries_cache:
            data, ts = self._countries_cache
            if now - ts < COUNTRIES_CACHE_TTL:
                return data
        data = await self.get("/countries")
        result = data if isinstance(data, list) else []
        self._countries_cache = (result, now)
        return result

    async def resolve_office_ids(
        self,
        *,
        office_ids: list[str] | None = None,
        country_codes: list[str] | None = None,
        regions: list[str] | None = None,
    ) -> list[str]:
        """Resolve a list of office IDs from explicit IDs, regions, or country codes.

        Precedence:
          1. ``office_ids`` → returned as-is.
          2. ``regions`` → resolved via ``regions.REGION_MAP`` to NO offices.
          3. ``country_codes`` → all offices across those countries.
          4. Fall back to ``self.default_country``.

        Raises ``FlowcaseConfigError`` when nothing resolves.
        """
        if office_ids:
            return list(office_ids)

        if regions:
            # Import here to avoid a cycle at module load time.
            from flowcase_mcp.regions import (
                REGION_MAP,
                resolve_regions_to_office_ids,
            )

            countries = await self.get_countries()
            info = resolve_regions_to_office_ids(
                regions, countries, country_code=self._default_country
            )
            if info["unknown_regions"]:
                raise FlowcaseConfigError(
                    f"Unknown region(s): {info['unknown_regions']!r}. "
                    f"Available: {sorted(REGION_MAP.keys())}"
                )
            if not info["office_ids"]:
                raise FlowcaseConfigError(
                    f"No offices matched regions {regions!r} in Flowcase."
                )
            return info["office_ids"]

        codes = [c.lower() for c in (country_codes or [self._default_country])]
        countries = await self.get_countries()
        resolved: list[str] = []
        for country in countries:
            if (country.get("code") or "").lower() in codes:
                for office in country.get("offices") or []:
                    oid = office.get("_id")
                    if oid:
                        resolved.append(oid)

        if not resolved:
            available = sorted(
                {(c.get("code") or "").lower() for c in countries if c.get("code")}
            )
            raise FlowcaseConfigError(
                f"No offices found for country codes {codes!r}. "
                f"Available: {available}"
            )
        return resolved

    async def get_user_ids_in_offices(
        self,
        office_ids: list[str],
        *,
        page_size: int = 100,
    ) -> set[str]:
        """Scan ``/search`` across the given offices and return all user IDs."""
        result: set[str] = set()
        offset = 0
        while True:
            query: list[tuple[str, Any]] = [("office_ids[]", oid) for oid in office_ids]
            query.append(("size", page_size))
            query.append(("from", offset))
            page = await self.get("/search", params=query)
            if not isinstance(page, list) or not page:
                break
            for user in page:
                uid = user.get("user_id") or user.get("_id")
                if uid:
                    result.add(uid)
            if len(page) < page_size:
                break
            offset += len(page)
            await asyncio.sleep(BULK_SCAN_PAGE_DELAY)
        return result

    # ------------------------------------------------------------------
    # Skill taxonomy caching + resolution
    # ------------------------------------------------------------------

    async def get_skill_taxonomy(
        self, *, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Return all approved skills (paginated) with caching."""
        now = time.time()
        if not force_refresh and self._skills_cache:
            data, ts = self._skills_cache
            if now - ts < SKILLS_CACHE_TTL:
                return data

        all_skills: list[dict[str, Any]] = []
        offset = 0
        page_size = 100
        while True:
            page = await self.get(
                "/masterdata/technologies/tags",
                params={"offset": offset, "limit": page_size},
            )
            if not isinstance(page, list) or not page:
                break
            all_skills.extend(page)
            if len(page) < page_size:
                break
            offset += len(page)
            await asyncio.sleep(BULK_SCAN_PAGE_DELAY)

        self._skills_cache = (all_skills, now)
        return all_skills

    async def resolve_skill_identifiers(
        self,
        inputs: list[str],
        *,
        lang: str = "no",
        match_mode: str = "exact",
    ) -> tuple[list[str], list[str], dict[str, list[str]]]:
        """Resolve skill names/IDs to canonical skill IDs.

        Each input is treated as an ID if it matches the 24-char hex pattern.
        Otherwise it's matched against language variants in the skill
        taxonomy according to ``match_mode``:

        * ``"exact"`` — case-insensitive equality (default; tightest)
        * ``"prefix"`` — label starts with the query
        * ``"substring"`` — label contains the query (loosest)

        Returns ``(resolved_ids, unresolved_inputs, per_input_matches)`` where
        ``per_input_matches`` maps each original name query to the list of
        resolved skill IDs so callers can expand/report per input.
        """
        mode = (match_mode or "exact").lower()
        if mode not in {"exact", "prefix", "substring"}:
            mode = "exact"

        resolved: list[str] = []
        unresolved: list[str] = []
        per_input: dict[str, list[str]] = {}
        name_queries: list[tuple[str, str]] = []

        for raw in inputs:
            text = (raw or "").strip()
            if not text:
                continue
            if OBJECT_ID_RE.match(text):
                resolved.append(text.lower())
                per_input[text] = [text.lower()]
            else:
                name_queries.append((text, text.lower()))

        if name_queries:
            taxonomy = await self.get_skill_taxonomy()
            for original, lowered in name_queries:
                matches: list[str] = []
                for skill in taxonomy:
                    sid = skill.get("_id")
                    if not sid:
                        continue
                    values = skill.get("values") or {}
                    if not isinstance(values, dict):
                        continue
                    for label in values.values():
                        if not isinstance(label, str):
                            continue
                        stripped = label.strip().lower()
                        if not stripped:
                            continue
                        hit = (
                            (mode == "exact" and stripped == lowered)
                            or (mode == "prefix" and stripped.startswith(lowered))
                            or (mode == "substring" and lowered in stripped)
                        )
                        if hit:
                            matches.append(sid)
                            break
                per_input[original] = matches
                if matches:
                    resolved.extend(matches)
                else:
                    unresolved.append(original)

        seen: set[str] = set()
        deduped: list[str] = []
        for sid in resolved:
            if sid not in seen:
                seen.add(sid)
                deduped.append(sid)
        return deduped, unresolved, per_input

    # ------------------------------------------------------------------
    # data_export/users bulk scan
    # ------------------------------------------------------------------

    async def get_all_users_via_data_export(
        self,
        *,
        force_refresh: bool = False,
    ) -> list[dict[str, Any]]:
        """Paginate ``/data_export/users`` and return every record (cached)."""
        now = time.time()
        if not force_refresh and self._data_export_users_cache:
            data, ts = self._data_export_users_cache
            if now - ts < DATA_EXPORT_CACHE_TTL:
                return data

        all_users: list[dict[str, Any]] = []
        offset = 0
        page_size = 100
        while True:
            resp = await self.get(
                "/data_export/users",
                params={"limit": page_size, "offset": offset},
            )
            if not isinstance(resp, dict):
                break
            values = resp.get("values") or []
            if not values:
                break
            all_users.extend(values)
            total = resp.get("total") or 0
            if total and len(all_users) >= total:
                break
            if len(values) < page_size:
                break
            offset += len(values)
            await asyncio.sleep(BULK_SCAN_PAGE_DELAY)

        self._data_export_users_cache = (all_users, now)
        return all_users


def format_http_error(exc: Exception) -> str:
    """Return an actionable error message for an httpx/network exception."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 401:
            return (
                "Authentication failed (401). Verify FLOWCASE_API_KEY and "
                "that the subscription is active."
            )
        if status == 403:
            return (
                "Permission denied (403). The subscription key may lack "
                "access to this endpoint."
            )
        if status == 404:
            return "Not found (404). Check that the ID or path is correct."
        if status == 429:
            return (
                "Rate limited (429) even after retries. Slow down or wait "
                "before retrying."
            )
        return f"API returned HTTP {status}."
    if isinstance(exc, httpx.TimeoutException):
        return "Request timed out. Flowcase proxy may be slow — retry shortly."
    if isinstance(exc, httpx.RequestError):
        return f"Network error: {type(exc).__name__}."
    if isinstance(exc, FlowcaseConfigError):
        return str(exc)
    return f"Unexpected error: {type(exc).__name__}."
