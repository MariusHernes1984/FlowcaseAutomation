import { Badge } from "@/components/ui";

import ConsultantCard from "./ConsultantCard";
import type { FindUsersBySkillData } from "./types";

export default function FindUsersResult({ data }: { data: FindUsersBySkillData }) {
  const total = data.total_matches ?? 0;
  const returned = data.returned ?? data.users?.length ?? 0;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs text-slate-600">
        <span className="font-medium text-slate-800">Scope:</span>
        <span>{data.scope ?? "—"}</span>
        {data.match_mode && (
          <Badge tone="neutral">mode: {data.match_mode}</Badge>
        )}
        {typeof data.match_all === "boolean" && (
          <Badge tone={data.match_all ? "blue" : "neutral"}>
            {data.match_all ? "AND" : "OR"}
          </Badge>
        )}
        <span className="ml-auto text-slate-700">
          <b>{returned}</b> viser av <b>{total}</b> treff
        </span>
      </div>

      {data.resolution_by_input && data.resolution_by_input.length > 0 && (
        <div className="rounded-md border border-slate-200 bg-slate-50 p-2 text-[11px] text-slate-600">
          <div className="mb-1 font-medium text-slate-700">Skills resolvert:</div>
          <ul className="space-y-0.5">
            {data.resolution_by_input.map((r) => (
              <li key={r.input}>
                <code className="text-slate-800">{r.input}</code> →{" "}
                {r.resolved_count} treff
                {r.resolved_names.length > 0 &&
                  `: ${r.resolved_names.slice(0, 4).join(", ")}${
                    r.resolved_names.length > 4
                      ? ` (+${r.resolved_names.length - 4})`
                      : ""
                  }`}
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.unresolved_inputs && data.unresolved_inputs.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-[11px] text-amber-800">
          Ikke gjenkjent: {data.unresolved_inputs.join(", ")}
        </div>
      )}

      {(data.users?.length ?? 0) === 0 ? (
        <div className="rounded-md border border-slate-200 bg-white p-4 text-center text-sm text-slate-500">
          Ingen konsulenter matchet kriteriene.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {data.users!.map((hit) => (
            <ConsultantCard key={hit.user_id ?? hit.email ?? hit.name} hit={hit} />
          ))}
        </div>
      )}
    </div>
  );
}
