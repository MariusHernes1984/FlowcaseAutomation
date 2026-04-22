import Sparkline from "./Sparkline";
import type { AvailabilityResultData } from "./types";

function pct(rate: number | null | undefined): string {
  if (typeof rate !== "number" || Number.isNaN(rate)) return "—";
  return `${Math.round(rate * 100)}%`;
}

export default function AvailabilityResult({
  data,
}: {
  data: AvailabilityResultData;
}) {
  return (
    <div className="flex items-center gap-5 rounded-lg border border-slate-200 bg-white p-4">
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-semibold text-slate-900">
          {data.name ?? "(uten navn)"}
        </div>
        <div className="mt-1 text-xs text-slate-500">
          {data.user_id && <span>user_id: {data.user_id.slice(0, 8)}… </span>}
        </div>
        <div className="mt-3 text-sm">
          <span className="text-emerald-700">
            {pct(data.avg_available)} ledig
          </span>
          <span className="ml-2 text-slate-500">
            ({pct(data.avg_billed)} booket)
          </span>
        </div>
      </div>
      {data.months && <Sparkline months={data.months} />}
    </div>
  );
}
