import { Building2, Users } from "lucide-react";

import { Badge } from "@/components/ui";

import type { Delivery, FindProjectsData } from "./types";

export default function FindProjectsResult({
  data,
}: {
  data: FindProjectsData;
}) {
  const deliveries = data.deliveries ?? [];
  const total = data.total ?? deliveries.length;
  const returned = data.returned ?? deliveries.length;
  const filters = data.filters ?? {};
  const unresolved = data.unresolved ?? {};
  const anyUnresolved =
    (unresolved.industries?.length ?? 0) +
      (unresolved.customers?.length ?? 0) +
      (unresolved.skills?.length ?? 0) >
    0;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs text-zinc-600">
        <span className="font-medium text-zinc-800">
          {returned} av {total} leveranser
        </span>
        {typeof data.candidates_scanned === "number" && (
          <span className="text-zinc-400">
            (scannet {data.candidates_scanned} CV-er)
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-1">
        {filters.industries?.map((i) => (
          <Badge key={`i-${i}`} tone="atea">
            bransje: {i}
          </Badge>
        ))}
        {filters.customers?.map((c) => (
          <Badge key={`c-${c}`} tone="blue">
            kunde: {c}
          </Badge>
        ))}
        {filters.skills?.map((s) => (
          <Badge key={`s-${s}`} tone="neutral">
            skill: {s}
          </Badge>
        ))}
        {filters.description_contains && (
          <Badge tone="neutral">tekst: "{filters.description_contains}"</Badge>
        )}
        {typeof filters.since_year === "number" && (
          <Badge tone="neutral">siden {filters.since_year}</Badge>
        )}
      </div>

      {anyUnresolved && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-2 text-[11px] text-amber-800">
          Ikke gjenkjent:{" "}
          {[
            ...(unresolved.industries ?? []).map((x) => `bransje '${x}'`),
            ...(unresolved.customers ?? []).map((x) => `kunde '${x}'`),
            ...(unresolved.skills ?? []).map((x) => `skill '${x}'`),
          ].join(", ")}
        </div>
      )}

      {deliveries.length === 0 ? (
        <div className="rounded-lg border border-zinc-200 bg-white p-5 text-center text-sm text-zinc-500">
          Ingen leveranser matchet filteret. Prøv bredere bransje eller
          <code className="mx-1 rounded bg-zinc-100 px-1">
            description_contains
          </code>
          med nøkkelord fra behovet.
        </div>
      ) : (
        <div className="space-y-2">
          {deliveries.map((d, i) => (
            <DeliveryCard key={`d-${i}-${d.customer}`} delivery={d} />
          ))}
        </div>
      )}
    </div>
  );
}

function DeliveryCard({ delivery }: { delivery: Delivery }) {
  const consultants = delivery.consultants ?? [];
  const skills = delivery.skills_used ?? [];
  const shownSkills = skills.slice(0, 12);
  const extraSkills = skills.length - shownSkills.length;
  const dates = `${delivery.from ?? "?"} → ${delivery.to || "nå"}`;

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-3 text-sm animate-fade-in">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-atea-600" />
            <span className="truncate font-semibold text-zinc-900">
              {delivery.customer ?? "(ukjent kunde)"}
            </span>
            {delivery.industry && <Badge tone="blue">{delivery.industry}</Badge>}
          </div>
          <div className="mt-1 text-xs text-zinc-500">{dates}</div>
        </div>
      </div>

      {delivery.description && (
        <p className="mt-3 whitespace-pre-wrap text-sm text-zinc-700">
          {delivery.description}
        </p>
      )}

      {shownSkills.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {shownSkills.map((s) => (
            <span
              key={s}
              className="rounded-md bg-zinc-100 px-2 py-0.5 text-[11px] font-medium text-zinc-700"
            >
              {s}
            </span>
          ))}
          {extraSkills > 0 && (
            <span className="rounded-md bg-zinc-200 px-2 py-0.5 text-[11px] text-zinc-600">
              +{extraSkills}
            </span>
          )}
        </div>
      )}

      <div className="mt-3 flex items-center gap-2 border-t border-zinc-100 pt-2 text-xs text-zinc-600">
        <Users className="h-3.5 w-3.5 text-zinc-400" />
        <span className="font-medium">{consultants.length} konsulent(er):</span>
        <span className="truncate">
          {consultants
            .map((c) => c.name)
            .filter(Boolean)
            .join(", ")}
        </span>
      </div>
    </div>
  );
}
