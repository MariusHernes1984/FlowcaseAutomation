# Flowcase Web — Frontend

Vite + React 18 + TypeScript + Tailwind. Communicates with the backend
(`../backend`) via a relative `/api` path that Vite proxies to
`http://localhost:8001` in dev, and that Static Web Apps rewrites in
production.

## Local dev

```powershell
npm install
npm run dev
```

Then visit <http://localhost:5173>. The homepage calls `/api/health`
against the backend to confirm wiring is alive.

## Path alias

Use `@/…` for `src/…` (configured in `tsconfig.json` + `vite.config.ts`):

```ts
import HomePage from "@/pages/HomePage";
```

## Next up (phase 3)

- Auth context + `/login` page
- Routing: `/`, `/chat/:agentId`, `/admin/*`
- shadcn/ui components (button, input, dialog)
- Streaming chat wiring against `/api/chat/:agentId`
