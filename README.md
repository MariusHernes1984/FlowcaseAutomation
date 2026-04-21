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
| `flowcase_find_users_by_skill` | Find consultants matching one or more skills |

All tools support `response_format="markdown"` (default) or `"json"`.

## Typical flows

### Look up a specific person
1. `flowcase_find_user(email=...)` → get `user_id` + `default_cv_id`
2. `flowcase_get_cv(user_id, cv_id)` → compact CV summary

### Find consultants by skill (Norway by default)
1. `flowcase_list_skills(query="python")` → verify the skill name / get ID
2. `flowcase_find_users_by_skill(skills=["python"])` → list of matching consultants (scoped to default country)
3. `flowcase_get_cv(user_id, cv_id)` for any candidate of interest

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
