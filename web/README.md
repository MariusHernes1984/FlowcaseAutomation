# Flowcase Web

Web-app for å snakke med Flowcase MCP-serveren via agenter. Består av:

- `frontend/` — Vite + React + TS + Tailwind
- `backend/` — FastAPI orchestrator (auth, Cosmos DB, Azure OpenAI, MCP-klient)
- `docker-compose.yml` — lokal dev-stack

## Fase-status

| Fase | Innhold | Status |
|---|---|---|
| 1 | Scaffolding: monorepo, FastAPI-shell, Vite-shell, Docker Compose | ✅ |
| 2 | Backend: Cosmos, admin-bootstrap, auth, agent-CRUD, chat-streaming | ⏳ |
| 3 | Frontend: login, chat-UI, admin-sider, shadcn/ui | ⏳ |
| 4 | Azure deploy: Bicep for Static Web App + Container App + Cosmos | ⏳ |

## Sikkerhet

- Brukere opprettes av admin (ingen åpen registrering)
- Passord hashes med bcrypt; JWT signeres med hemmelighet fra Key Vault
- Chat-historikk inneholder PII (CV-data) → per-bruker partition i Cosmos
- Alle kall fra frontend går via egen backend — verken LLM-nøkkel,
  MCP-nøkkel eller Cosmos-nøkkel eksponeres til nettleseren

## Rekkefølge for lokal oppstart (når fase 2 er ferdig)

```powershell
# Terminal 1 — backend
cd web/backend
copy .env.example .env
# fyll inn .env
docker compose -f ../docker-compose.yml up --build backend

# Terminal 2 — frontend
cd web/frontend
npm install
npm run dev
```
