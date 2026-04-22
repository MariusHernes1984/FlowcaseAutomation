import type { ListCustomersData } from "./types";

export default function ListCustomersResult({
  data,
}: {
  data: ListCustomersData;
}) {
  const customers = data.customers ?? [];
  return (
    <div className="space-y-2">
      <div className="text-xs text-zinc-600">
        <b>{data.count ?? customers.length}</b> av <b>{data.total ?? "?"}</b>{" "}
        kunder
        {data.has_more && " (flere tilgjengelig)"}
      </div>
      {customers.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {customers.map((c) => (
            <span
              key={c.customer_id}
              className="rounded-md border border-zinc-200 bg-white px-2 py-0.5 text-[11px] text-zinc-700"
              title={c.customer_id}
            >
              {c.name}
            </span>
          ))}
        </div>
      ) : (
        <div className="text-xs italic text-zinc-500">Ingen kunder.</div>
      )}
    </div>
  );
}
