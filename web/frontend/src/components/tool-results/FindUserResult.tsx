import { Badge } from "@/components/ui";

import type { FindUserData } from "./types";

export default function FindUserResult({ data }: { data: FindUserData }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-3 text-sm">
      <div className="flex items-center gap-2">
        <span className="font-semibold text-slate-900">
          {data.name ?? "(uten navn)"}
        </span>
        {data.role && <Badge tone="blue">{data.role}</Badge>}
        {data.deactivated && <Badge tone="red">deaktivert</Badge>}
      </div>
      {data.title && (
        <div className="text-xs text-slate-500 italic">{data.title}</div>
      )}
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {data.email && (
          <div>
            <dt className="text-slate-400">Epost</dt>
            <dd className="text-slate-700">{data.email}</dd>
          </div>
        )}
        {data.external_unique_id && (
          <div>
            <dt className="text-slate-400">ATEA-ID</dt>
            <dd className="font-mono text-slate-700">
              {data.external_unique_id}
            </dd>
          </div>
        )}
        {data.office_name && (
          <div>
            <dt className="text-slate-400">Kontor</dt>
            <dd className="text-slate-700">
              {data.office_name}
              {data.country_code && ` · ${data.country_code.toUpperCase()}`}
            </dd>
          </div>
        )}
        {data.user_id && (
          <div>
            <dt className="text-slate-400">user_id</dt>
            <dd className="font-mono text-[10px] text-slate-500">
              {data.user_id}
            </dd>
          </div>
        )}
        {data.default_cv_id && (
          <div>
            <dt className="text-slate-400">cv_id</dt>
            <dd className="font-mono text-[10px] text-slate-500">
              {data.default_cv_id}
            </dd>
          </div>
        )}
      </dl>
    </div>
  );
}
