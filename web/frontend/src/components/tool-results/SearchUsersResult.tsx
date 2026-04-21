import ConsultantCard from "./ConsultantCard";
import type { SearchUsersData } from "./types";

export default function SearchUsersResult({ data }: { data: SearchUsersData }) {
  const users = data.users ?? [];
  return (
    <div className="space-y-2">
      <div className="text-xs text-slate-600">
        Viser <b>{users.length}</b> brukere fra offset {data.from ?? 0}
        {data.has_more &&
          ` (flere tilgjengelig — next_from=${data.next_from ?? "?"})`}
      </div>
      {users.length === 0 ? (
        <div className="rounded-md border border-slate-200 bg-white p-3 text-center text-xs text-slate-500">
          Ingen brukere.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {users.map((u) => (
            <ConsultantCard key={u.user_id ?? u.email ?? u.name} hit={u} />
          ))}
        </div>
      )}
    </div>
  );
}
