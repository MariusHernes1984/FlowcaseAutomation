# Flowcase Web — Backend

FastAPI orchestrator that sits between the React frontend and the
downstream services (Azure OpenAI, the Flowcase MCP, Cosmos DB).

## Local dev

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
# fill in secrets in .env
uvicorn flowcase_web.main:app --reload --port 8001
```

Visit <http://localhost:8001/health> — should return `{"status":"ok"}`.

## Next up (phase 2)

- Cosmos client + admin bootstrap
- `/auth/login`, `/auth/refresh`, `/auth/me`
- Agent CRUD under `/agents` (admin-only)
- `/chat/{agent_id}` streaming endpoint using Azure OpenAI + MCP tools
