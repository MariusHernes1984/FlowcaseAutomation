import type { ListIndustriesData } from "./types";

export default function ListIndustriesResult({
  data,
}: {
  data: ListIndustriesData;
}) {
  const industries = data.industries ?? [];
  return (
    <div className="space-y-2">
      <div className="text-xs text-zinc-600">
        <b>{data.count ?? industries.length}</b> av <b>{data.total ?? "?"}</b>{" "}
        bransjer
        {data.has_more && " (flere tilgjengelig)"}
      </div>
      {industries.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {industries.map((i) => (
            <span
              key={i.industry_id}
              className="rounded-md border border-atea-200 bg-atea-50 px-2 py-0.5 text-[11px] font-medium text-atea-800"
              title={i.industry_id}
            >
              {i.name}
            </span>
          ))}
        </div>
      ) : (
        <div className="text-xs italic text-zinc-500">Ingen bransjer.</div>
      )}
    </div>
  );
}
