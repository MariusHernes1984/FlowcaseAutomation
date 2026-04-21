import { useQuery } from "@tanstack/react-query";
import axios from "axios";

interface HealthResponse {
  status: string;
  env: string;
}

export default function HomePage() {
  const { data, isLoading, error } = useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: async () => {
      const r = await axios.get<HealthResponse>("/api/health");
      return r.data;
    },
    retry: false,
  });

  return (
    <div className="space-y-6">
      <section>
        <h1 className="text-3xl font-semibold tracking-tight">
          Flowcase web — scaffolding
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Dette er en tom React-shell. Neste steg: login, agent-oversikt,
          chat-UI, og admin-side for å redigere system-prompt per agent.
        </p>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-medium uppercase tracking-wider text-slate-500">
          Backend helsesjekk
        </h2>
        <div className="mt-2 font-mono text-sm">
          {isLoading && <span className="text-slate-500">kaller /api/health…</span>}
          {error && (
            <span className="text-red-600">
              feil: {(error as Error).message}
            </span>
          )}
          {data && (
            <span className="text-emerald-700">
              {data.status} · env={data.env}
            </span>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-dashed border-slate-300 p-5 text-sm text-slate-500">
        <p>Kommende fase 2-routes:</p>
        <ul className="mt-2 list-inside list-disc">
          <li>/login — brukernavn + passord</li>
          <li>/chat/:agentId — samtaler mot agent (streaming)</li>
          <li>/admin/agents — CRUD på system-prompter</li>
          <li>/admin/users — admin oppretter/deaktiverer brukere</li>
        </ul>
      </section>
    </div>
  );
}
