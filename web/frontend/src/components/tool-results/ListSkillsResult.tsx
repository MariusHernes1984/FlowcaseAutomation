import type { ListSkillsData } from "./types";

export default function ListSkillsResult({ data }: { data: ListSkillsData }) {
  const skills = data.skills ?? [];
  return (
    <div className="space-y-2">
      <div className="text-xs text-slate-600">
        <b>{data.count ?? skills.length}</b> av <b>{data.total ?? "?"}</b> skills
        {data.has_more && " (flere tilgjengelig)"}
      </div>
      {skills.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {skills.map((s) => (
            <span
              key={s.skill_id}
              className="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-700"
              title={s.skill_id}
            >
              {s.name}
            </span>
          ))}
        </div>
      ) : (
        <div className="text-xs italic text-slate-500">Ingen skills.</div>
      )}
    </div>
  );
}
