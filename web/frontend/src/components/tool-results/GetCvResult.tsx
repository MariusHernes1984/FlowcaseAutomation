import type { CvData } from "./types";

export default function GetCvResult({ data }: { data: CvData }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
      <div className="flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-slate-900">
            {data.name ?? "(uten navn)"}
          </h3>
          {data.title && (
            <div className="text-xs text-slate-500 italic">{data.title}</div>
          )}
        </div>
        <div className="text-right text-[11px] text-slate-500">
          {data.place_of_residence && <div>{data.place_of_residence}</div>}
          {data.email && <div>{data.email}</div>}
        </div>
      </div>

      {data.key_qualifications && data.key_qualifications.length > 0 && (
        <Section title="Kjernekompetanse">
          <ul className="space-y-1">
            {data.key_qualifications.map((k, i) => (
              <li key={i} className="text-xs">
                {k.label && <b className="text-slate-800">{k.label}</b>}
                {k.label && k.summary && ": "}
                {k.summary}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {data.technologies && data.technologies.length > 0 && (
        <Section title="Teknologier">
          <div className="space-y-1 text-xs">
            {data.technologies.map((t, i) => (
              <div key={i}>
                {t.category && (
                  <span className="mr-2 font-medium text-slate-700">
                    {t.category}:
                  </span>
                )}
                <span className="text-slate-600">
                  {(t.skills ?? []).join(", ")}
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {data.recent_projects && data.recent_projects.length > 0 && (
        <Section title="Nylige prosjekter">
          <div className="space-y-3">
            {data.recent_projects.map((p, i) => (
              <div
                key={i}
                className="border-l-2 border-slate-200 pl-3 text-xs"
              >
                <div className="font-semibold text-slate-800">
                  {p.customer ?? "(kunde ukjent)"}
                </div>
                {(p.from || p.to) && (
                  <div className="text-[11px] text-slate-500">
                    {p.from ?? "?"} – {p.to ?? "nå"}
                    {p.industry && ` · ${p.industry}`}
                  </div>
                )}
                {p.description && (
                  <div className="mt-1 text-slate-600">{p.description}</div>
                )}
                {p.roles && p.roles.length > 0 && (
                  <div className="mt-1 text-[11px] text-slate-500">
                    Roller: {p.roles.join("; ")}
                  </div>
                )}
                {p.skills && p.skills.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {p.skills.map((s) => (
                      <span
                        key={s}
                        className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-700"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {data.certifications && data.certifications.length > 0 && (
        <Section title="Sertifiseringer">
          <ul className="space-y-0.5 text-xs text-slate-700">
            {data.certifications.map((c, i) => (
              <li key={i}>
                {c.name}
                {c.organiser && ` — ${c.organiser}`}
                {c.year && ` (${c.year})`}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {data.languages && data.languages.length > 0 && (
        <Section title="Språk">
          <div className="flex flex-wrap gap-1 text-[11px]">
            {data.languages.map((l, i) => (
              <span
                key={i}
                className="rounded bg-slate-100 px-2 py-0.5 text-slate-700"
              >
                {l.name}
                {l.level && ` (${l.level})`}
              </span>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-4 border-t border-slate-100 pt-3">
      <h4 className="mb-2 text-[11px] font-medium uppercase tracking-wide text-slate-500">
        {title}
      </h4>
      {children}
    </div>
  );
}
