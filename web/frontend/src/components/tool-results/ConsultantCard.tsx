import { Badge } from "@/components/ui";

import Sparkline from "./Sparkline";
import type { AvailabilityData, ConsultantHit } from "./types";

function pct(rate: number | null | undefined): string {
  if (typeof rate !== "number" || Number.isNaN(rate)) return "—";
  return `${Math.round(rate * 100)}%`;
}

function capacityTone(
  avail?: AvailabilityData | null,
): { label: string; tone: "green" | "amber" | "red" | "neutral" } {
  const billed = avail?.avg_billed;
  if (typeof billed !== "number") return { label: "ingen data", tone: "neutral" };
  if (billed < 0.5) return { label: "✅ ledig", tone: "green" };
  if (billed < 0.8) return { label: "🟡 fullt opp", tone: "amber" };
  return { label: "🔴 begrenset", tone: "red" };
}

export default function ConsultantCard({ hit }: { hit: ConsultantHit }) {
  const cap = capacityTone(hit.availability);
  const matching = hit.matching_skills ?? [];
  const shownSkills = matching.slice(0, 8);
  const extra = matching.length - shownSkills.length;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate font-semibold text-slate-900">
              {hit.name ?? "(uten navn)"}
            </span>
            <Badge tone={cap.tone}>{cap.label}</Badge>
            {hit.deactivated && <Badge tone="red">deaktivert</Badge>}
          </div>
          {hit.email && (
            <a
              href={`mailto:${hit.email}`}
              className="block truncate text-xs text-slate-500 hover:underline"
            >
              {hit.email}
            </a>
          )}
          {hit.office_name && (
            <div className="text-xs text-slate-500">
              {hit.office_name}
              {hit.country_code && ` · ${hit.country_code.toUpperCase()}`}
            </div>
          )}
        </div>

        {hit.availability?.months && (
          <div className="flex flex-col items-end gap-1">
            <Sparkline months={hit.availability.months} />
            <div className="text-[11px] text-slate-500">
              snitt {pct(hit.availability.avg_billed)} booket
            </div>
          </div>
        )}
      </div>

      {shownSkills.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {shownSkills.map((s) => (
            <span
              key={s}
              className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-700"
            >
              {s}
            </span>
          ))}
          {extra > 0 && (
            <span className="rounded-md bg-slate-200 px-2 py-0.5 text-[11px] text-slate-600">
              +{extra}
            </span>
          )}
        </div>
      )}

      {typeof hit.total_skills === "number" && matching.length > 0 && (
        <div className="mt-2 text-[11px] text-slate-400">
          {matching.length} matchende av {hit.total_skills} skills på CV
        </div>
      )}
    </div>
  );
}
