import type { ListOfficesData } from "./types";

export default function ListOfficesResult({ data }: { data: ListOfficesData }) {
  return (
    <div className="space-y-3">
      {data.map((country) => (
        <div
          key={country.country_id}
          className="rounded-md border border-slate-200 bg-white p-3"
        >
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {country.country_code}
          </div>
          <div className="grid grid-cols-2 gap-1 md:grid-cols-3">
            {country.offices.map((o) => (
              <div
                key={o.office_id}
                className="flex items-baseline justify-between rounded bg-slate-50 px-2 py-1 text-xs"
              >
                <span className="truncate font-medium text-slate-700">
                  {o.office_name}
                </span>
                <span className="text-slate-500">{o.num_users ?? 0}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
