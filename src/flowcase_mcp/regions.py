"""Atea region mapping for Norwegian Flowcase offices.

Atea organizes the ~24 Norwegian offices into five geographical regions.
This is an Atea-specific business layer, not a Flowcase API concept, so
it lives separately from the client.

The mapping keys are lowercase region names. Aliases (English forms,
spelling variants) normalize to the canonical keys.

To use a region in a tool call, pass ``regions=["sør", "vest"]`` to any
search tool that supports it. Regions are resolved to Flowcase office
IDs by matching office names against ``/countries`` (cached).
"""

from __future__ import annotations

from typing import Any

# Canonical region → list of office names (as they appear in Flowcase)
REGION_MAP: dict[str, list[str]] = {
    "øst": ["Oslo", "Hamar", "Fredrikstad"],
    "sør": [
        "Drammen",
        "Kongsberg",
        "Sandefjord",
        "Arendal",
        "Kristiansand",
    ],
    "sørvest": ["Stavanger", "Haugesund", "Stord"],
    "vest": [
        "Bergen",
        "Fosnavåg",
        "Førde",
        "Kristiansund",
        "Ålesund",
    ],
    "nord": [
        "Trondheim",
        "Steinkjer",
        "Bodø",
        "Tromsø",
        "Alta",
        "Hammerfest",
    ],
}

# Normalization map: alternative spellings/translations → canonical key
REGION_ALIASES: dict[str, str] = {
    "sor": "sør",
    "syd": "sør",
    "south": "sør",
    "sorvest": "sørvest",
    "sør-vest": "sørvest",
    "sor-vest": "sørvest",
    "syd-vest": "sørvest",
    "south-west": "sørvest",
    "southwest": "sørvest",
    "east": "øst",
    "ost": "øst",
    "west": "vest",
    "north": "nord",
    "midt": "nord",
    "mid": "nord",
    "central": "nord",
}


def canonical_region(name: str) -> str | None:
    """Normalize a region label. Returns the canonical key or None if unknown."""
    if not name:
        return None
    key = name.strip().lower()
    key = REGION_ALIASES.get(key, key)
    if key in REGION_MAP:
        return key
    return None


def resolve_regions_to_office_ids(
    regions: list[str],
    countries_data: list[dict[str, Any]],
    *,
    country_code: str = "no",
) -> dict[str, Any]:
    """Resolve a list of region names to Flowcase office IDs.

    Given the ``/countries`` payload, builds a case-insensitive
    name-to-id map for the target country's offices and matches each
    region's office names against it.

    Returns a dict with:
        - ``office_ids``: deduplicated list of matched office IDs
        - ``matched``: list of (region, office_name, office_id, num_users)
          tuples for offices actually found in Flowcase
        - ``missing_offices``: list of (region, office_name) tuples for
          names in REGION_MAP that weren't found in Flowcase (e.g., Molde)
        - ``unknown_regions``: list of input strings that didn't resolve
          to a known region
    """
    # Build lowercase name → (id, num_users) lookup for the target country
    name_to_office: dict[str, tuple[str, int | None]] = {}
    for country in countries_data or []:
        if (country.get("code") or "").lower() != country_code.lower():
            continue
        for office in country.get("offices") or []:
            name = office.get("name")
            oid = office.get("_id")
            if isinstance(name, str) and oid:
                name_to_office[name.lower()] = (oid, office.get("num_users"))

    office_ids: list[str] = []
    matched: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    unknown_regions: list[str] = []
    seen_ids: set[str] = set()

    for region in regions or []:
        key = canonical_region(region)
        if key is None:
            unknown_regions.append(region)
            continue
        for office_name in REGION_MAP[key]:
            found = name_to_office.get(office_name.lower())
            if found is None:
                missing.append({"region": key, "office_name": office_name})
                continue
            oid, num_users = found
            if oid in seen_ids:
                continue
            seen_ids.add(oid)
            office_ids.append(oid)
            matched.append(
                {
                    "region": key,
                    "office_name": office_name,
                    "office_id": oid,
                    "num_users": num_users,
                }
            )

    return {
        "office_ids": office_ids,
        "matched": matched,
        "missing_offices": missing,
        "unknown_regions": unknown_regions,
    }


def region_overview(
    countries_data: list[dict[str, Any]],
    *,
    country_code: str = "no",
) -> list[dict[str, Any]]:
    """Build a region-by-region summary with offices and user counts."""
    out: list[dict[str, Any]] = []
    for region in REGION_MAP:
        info = resolve_regions_to_office_ids(
            [region], countries_data, country_code=country_code
        )
        total_users = sum(
            (m.get("num_users") or 0) for m in info["matched"]
        )
        out.append(
            {
                "region": region,
                "matched_offices": info["matched"],
                "missing_offices": info["missing_offices"],
                "num_offices": len(info["matched"]),
                "num_users": total_users,
            }
        )
    return out
