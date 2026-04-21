import type { ListRegionsData } from "./types";

export default function ListRegionsResult({ data }: { data: ListRegionsData }) {
  const regions = data.regions ?? [];
  return (
    <div className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3">
      {regions.map((r) => (
        <div
          key={r.region}
          className="rounded-md border border-slate-200 bg-white p-3"
        >
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-semibold text-slate-800 capitalize">
              {r.region}
            </span>
            <span className="text-xs text-slate-500">
              {r.num_offices} kontor · {r.num_users} brukere
            </span>
          </div>
          <div className="mt-2 flex flex-wrap gap-1">
            {r.matched_offices.map((o) => (
              <span
                key={o.office_id}
                className="rounded bg-slate-100 px-2 py-0.5 text-[11px] text-slate-700"
              >
                {o.office_name}
                {typeof o.num_users === "number" && (
                  <span className="ml-1 text-slate-400">{o.num_users}</span>
                )}
              </span>
            ))}
          </div>
          {r.missing_offices.length > 0 && (
            <div className="mt-2 text-[11px] text-amber-700">
              Ikke i Flowcase:{" "}
              {r.missing_offices.map((m) => m.office_name).join(", ")}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
