# Flowcase MCP

MCP server for **Atea Flowcase** via the ServiceHub proxy
(`https://servicehub.atea.com/flowcase`).

Exposes read-only tools so MCP clients (Claude Code, Claude Desktop, etc.) can
discover Atea consultants, look up users, and fetch CVs.

## Status

Version 0.1 — MVP with four read-only tools. Write endpoints (create/update
user, create office, initiate report, create tag) are intentionally not
exposed yet; they will be added once the read-only flow is battle-tested.

## Prerequisites

- Python 3.11 or newer
- A Flowcase subscription key from Atea ServiceHub

## Setup

```powershell
# 1. Create and activate a virtualenv
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install in editable mode
pip install -e .

# 3. Configure credentials
copy .env.example .env
# ...then edit .env and paste your subscription key
```

## Run

```powershell
flowcase-mcp
```

The server speaks MCP over stdio. Run it from an MCP client rather than
interactively.

## Hook into Claude Code

Add to your `.mcp.json` (project-scoped) or to your global Claude Code config:

```json
{
  "mcpServers": {
    "flowcase": {
      "command": "flowcase-mcp",
      "env": {
        "FLOWCASE_API_KEY": "your-subscription-key-here"
      }
    }
  }
}
```

If you prefer loading the key from `.env` (recommended for development), drop
the `env` block and ensure `.env` is in the same working directory the client
launches the server from.

## Tools

| Tool | Purpose |
|---|---|
| `flowcase_list_offices` | List countries and offices with IDs |
| `flowcase_search_users` | List users within offices or countries (paginated) |
| `flowcase_find_user` | Look up a single user by email or Atea domain username |
| `flowcase_get_cv` | Fetch a CV — compact by section, `verbose=true` for full raw data |
| `flowcase_list_skills` | Browse the skill taxonomy (name + ID) |
| `flowcase_find_users_by_skill` | Find consultants matching one or more skills (optionally filtered by availability) |
| `flowcase_get_availability` | Monthly billing rate for a single consultant |
| `flowcase_list_regions` | Show Atea NO region mapping (Øst/Sør/Sørvest/Vest/Nord) |

All tools support `response_format="markdown"` (default) or `"json"`.

## Typical flows

### Look up a specific person
1. `flowcase_find_user(email=...)` → get `user_id` + `default_cv_id`
2. `flowcase_get_cv(user_id, cv_id)` → compact CV summary

### Find consultants by skill (Norway by default)

**Precise lookup (recommended):**
1. `flowcase_list_skills(query="azure")` → browse taxonomy, note exact names / IDs
2. `flowcase_find_users_by_skill(skills=["Microsoft Azure"])` → exact match by default
3. `flowcase_get_cv(user_id, cv_id)` for each candidate

**Combine multiple skills (AND):**
```
flowcase_find_users_by_skill(
  skills=["Microsoft Azure", "Terraform"],
  match_all=true
)
```

**Explore broadly:**
```
flowcase_find_users_by_skill(
  skills=["azure"],
  match_mode="substring"   # matches Azure AD, Azure AI, etc.
)
```

### Match modes

| Mode | Behavior | Example |
|---|---|---|
| `exact` (default) | Case-insensitive equality | `"Python"` → only "Python" |
| `prefix` | Starts-with match | `"Python"` → Python, Python 2, Python 3 |
| `substring` | Contains match (broadest) | `"python"` → + IronPython, CPython |

Raw skill IDs (24-char hex) always bypass name matching and work in any mode.

### Availability (consultant capacity)

The server can enrich skill-search results with monthly billing rates
from a PowerBI export (the "PBI KONsulent.xlsx" workbook). Place the
file at `data/availability.xlsx` or set `FLOWCASE_AVAILABILITY_PATH`.
The file auto-reloads when its mtime changes — no restart required.

**Filter by availability:**
```
flowcase_find_users_by_skill(
  skills=["Microsoft Azure", "Terraform"],
  match_all=true,
  max_avg_billed=0.6    # only return people ≤60% booked on avg
)
```
Results are sorted by availability (most available first) when this
filter is set.

**Direct lookup:**
```
flowcase_get_availability(name="Aaron Jimenez")
flowcase_get_availability(email="aaron.jimenez@atea.no")
flowcase_get_availability(user_id="5c4a...")
```

Matching is by display name (case- and token-order-insensitive). If a
consultant isn't in the workbook, the tool returns a clear message.

### Atea NO regions

The five Atea Norway regions map to these offices:

| Region | Offices |
|---|---|
| **Øst** | Oslo, Hamar, Fredrikstad |
| **Sør** | Drammen, Kongsberg, Sandefjord, Arendal, Kristiansand |
| **Sørvest** | Stavanger, Haugesund, Stord |
| **Vest** | Bergen, Fosnavåg, Førde, Kristiansund, Ålesund |
| **Nord** | Trondheim, Steinkjer, Bodø, Tromsø, Alta, Hammerfest |

Pass `regions=["sør"]` (or aliases like `south`, `sor`) to either
`flowcase_search_users` or `flowcase_find_users_by_skill` to scope by
region instead of individual offices. Call `flowcase_list_regions` to
see live user counts per region.

### Browse by office
1. `flowcase_list_offices(country_codes=["no"])` → office IDs
2. `flowcase_search_users(office_ids=[...])` → paginated list

## Important notes on search behavior

The `/search` endpoint on the Atea proxy does NOT accept text or skill
filters — `q=`, `must[]`, etc. are silently ignored. Skill-based discovery
therefore goes through `/data_export/users` (4 000+ records with skill IDs
per user) combined with the skill taxonomy. The client caches both for
efficient repeated queries.

## Security notes

- **Production credentials.** `.env` holds a live Flowcase subscription key.
  It is gitignored and must not be committed.
- **PII.** CVs contain names, emails, phone numbers, and work history. The
  server never logs response bodies. Downstream MCP clients decide what to
  store in their own transcripts — be mindful.
- **Read-only by design.** Version 0.1 only calls `GET` endpoints. No user
  records, CVs, or masterdata can be modified through this MCP.

## OpenAPI reference

`openapi.json` is the Flowcase proxy spec retrieved from ServiceHub. Keep it
in sync if the proxy surface changes.

## Project layout

```
src/flowcase_mcp/
  __init__.py
  __main__.py       # console entry point
  client.py         # async HTTP client + error formatting
  formatting.py     # multilang helpers + CV compaction
  server.py         # MCP tool definitions
```
