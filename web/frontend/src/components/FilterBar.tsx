import { X } from "lucide-react";
import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  fetchCustomers,
  fetchIndustries,
  fetchRegions,
  fetchSkills,
} from "@/api/reference";

export interface ChatFilters {
  industries: string[];
  customers: string[];
  skills: string[];
  region: string | null;
  since_year: number | null;
}

export const EMPTY_FILTERS: ChatFilters = {
  industries: [],
  customers: [],
  skills: [],
  region: null,
  since_year: null,
};

export function filtersToPrompt(filters: ChatFilters): string {
  const parts: string[] = [];
  if (filters.industries.length)
    parts.push(`bransje=${filters.industries.join(", ")}`);
  if (filters.customers.length)
    parts.push(`kunde=${filters.customers.join(", ")}`);
  if (filters.skills.length)
    parts.push(`skills=${filters.skills.join(", ")}`);
  if (filters.region) parts.push(`region=${filters.region}`);
  if (typeof filters.since_year === "number")
    parts.push(`siden_år=${filters.since_year}`);
  if (parts.length === 0) return "";
  return `[Aktive filter: ${parts.join(" · ")}]`;
}

export function filtersAreEmpty(filters: ChatFilters): boolean {
  return (
    filters.industries.length === 0 &&
    filters.customers.length === 0 &&
    filters.skills.length === 0 &&
    filters.region === null &&
    filters.since_year === null
  );
}

interface FilterBarProps {
  filters: ChatFilters;
  onChange: (f: ChatFilters) => void;
  agentId: string | null;
}

export default function FilterBar({ filters, onChange, agentId }: FilterBarProps) {
  const isProjects = agentId === "referanse-finner";
  const isPeople = agentId === "konsulent-finner";

  // All chip definitions — we render based on agent role.
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {/* Always show skills */}
      <SkillsChip filters={filters} onChange={onChange} />

      {/* Project-finder-flavoured */}
      {isProjects && (
        <>
          <IndustryChip filters={filters} onChange={onChange} />
          <CustomerChip filters={filters} onChange={onChange} />
          <SinceYearChip filters={filters} onChange={onChange} />
        </>
      )}

      {/* Consultant-finder-flavoured */}
      {isPeople && <RegionChip filters={filters} onChange={onChange} />}

      {!filtersAreEmpty(filters) && (
        <button
          onClick={() => onChange({ ...EMPTY_FILTERS })}
          className="ml-2 text-[11px] text-zinc-500 hover:text-zinc-800"
        >
          Nullstill alle
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared chip primitives
// ---------------------------------------------------------------------------

function AddChip({
  label,
  open,
  onOpen,
}: {
  label: string;
  open: boolean;
  onOpen: () => void;
}) {
  return (
    <button
      onClick={onOpen}
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium transition ${
        open
          ? "border-atea-400 bg-atea-50 text-atea-800"
          : "border-dashed border-zinc-300 bg-white text-zinc-600 hover:border-zinc-400 hover:bg-zinc-50"
      }`}
    >
      <span className="text-zinc-400">+</span>
      {label}
    </button>
  );
}

function ValueChip({
  label,
  value,
  onRemove,
  onClick,
  tone = "atea",
}: {
  label: string;
  value: string;
  onRemove: () => void;
  onClick?: () => void;
  tone?: "atea" | "blue" | "neutral";
}) {
  const toneClass = {
    atea: "border-atea-200 bg-atea-50 text-atea-900",
    blue: "border-blue-200 bg-blue-50 text-blue-900",
    neutral: "border-zinc-200 bg-zinc-100 text-zinc-800",
  }[tone];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium ${toneClass}`}
    >
      <button
        onClick={onClick}
        className="cursor-pointer hover:underline"
        title="Endre"
      >
        <span className="opacity-70">{label}:</span> {value}
      </button>
      <button
        onClick={onRemove}
        className="ml-0.5 -mr-1 rounded-full p-0.5 hover:bg-black/10"
        aria-label={`Fjern ${label}`}
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

function Popover({
  open,
  onClose,
  children,
}: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const onEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onEsc);
    };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div
      ref={ref}
      className="absolute z-10 mt-1 w-72 overflow-hidden rounded-lg border border-zinc-200 bg-white shadow-floating"
    >
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Autocomplete helper
// ---------------------------------------------------------------------------

function useDebouncedQuery<T>(
  query: string,
  fetcher: (q: string) => Promise<T[]>,
  delay = 200,
) {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const t = setTimeout(() => {
      fetcher(query)
        .then((res) => {
          if (!cancelled) setItems(res);
        })
        .catch(() => {
          if (!cancelled) setItems([]);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, delay);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query, fetcher, delay]);
  return { items, loading };
}

function AutocompleteList<T extends { name: string }>({
  items,
  loading,
  onPick,
  empty,
}: {
  items: T[];
  loading: boolean;
  onPick: (name: string) => void;
  empty?: string;
}) {
  return (
    <div className="max-h-64 overflow-y-auto py-1 text-sm">
      {loading && (
        <div className="px-3 py-2 text-xs text-zinc-400">Laster…</div>
      )}
      {!loading && items.length === 0 && (
        <div className="px-3 py-2 text-xs text-zinc-400">
          {empty ?? "Ingen treff"}
        </div>
      )}
      {items.map((it) => (
        <button
          key={it.name}
          onClick={() => onPick(it.name)}
          className="block w-full truncate px-3 py-1.5 text-left hover:bg-zinc-100"
        >
          {it.name}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Specific chips
// ---------------------------------------------------------------------------

function IndustryChip({
  filters,
  onChange,
}: {
  filters: ChatFilters;
  onChange: (f: ChatFilters) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const inputId = useId();
  const { items, loading } = useDebouncedQuery(query, fetchIndustries);

  const add = (name: string) => {
    if (!filters.industries.includes(name)) {
      onChange({ ...filters, industries: [...filters.industries, name] });
    }
    setQuery("");
    setOpen(false);
  };

  return (
    <>
      {filters.industries.map((name) => (
        <ValueChip
          key={name}
          label="Bransje"
          value={name}
          onRemove={() =>
            onChange({
              ...filters,
              industries: filters.industries.filter((x) => x !== name),
            })
          }
          tone="atea"
        />
      ))}
      <div className="relative">
        <AddChip label="Bransje" open={open} onOpen={() => setOpen(true)} />
        <Popover open={open} onClose={() => setOpen(false)}>
          <div className="border-b border-zinc-100 p-2">
            <input
              autoFocus
              id={inputId}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Søk bransje…"
              className="w-full rounded-md border border-zinc-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-atea-500/20"
            />
          </div>
          <AutocompleteList items={items} loading={loading} onPick={add} />
        </Popover>
      </div>
    </>
  );
}

function CustomerChip({
  filters,
  onChange,
}: {
  filters: ChatFilters;
  onChange: (f: ChatFilters) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const { items, loading } = useDebouncedQuery(query, fetchCustomers);

  const add = (name: string) => {
    if (!filters.customers.includes(name)) {
      onChange({ ...filters, customers: [...filters.customers, name] });
    }
    setQuery("");
    setOpen(false);
  };

  return (
    <>
      {filters.customers.map((name) => (
        <ValueChip
          key={name}
          label="Kunde"
          value={name}
          onRemove={() =>
            onChange({
              ...filters,
              customers: filters.customers.filter((x) => x !== name),
            })
          }
          tone="blue"
        />
      ))}
      <div className="relative">
        <AddChip label="Kunde" open={open} onOpen={() => setOpen(true)} />
        <Popover open={open} onClose={() => setOpen(false)}>
          <div className="border-b border-zinc-100 p-2">
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Søk kunde…"
              className="w-full rounded-md border border-zinc-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-atea-500/20"
            />
          </div>
          <AutocompleteList items={items} loading={loading} onPick={add} />
        </Popover>
      </div>
    </>
  );
}

function SkillsChip({
  filters,
  onChange,
}: {
  filters: ChatFilters;
  onChange: (f: ChatFilters) => void;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const { items, loading } = useDebouncedQuery(query, fetchSkills);

  const add = (name: string) => {
    if (!filters.skills.includes(name)) {
      onChange({ ...filters, skills: [...filters.skills, name] });
    }
    setQuery("");
    setOpen(false);
  };

  return (
    <>
      {filters.skills.map((name) => (
        <ValueChip
          key={name}
          label="Skill"
          value={name}
          onRemove={() =>
            onChange({
              ...filters,
              skills: filters.skills.filter((x) => x !== name),
            })
          }
          tone="neutral"
        />
      ))}
      <div className="relative">
        <AddChip label="Skill" open={open} onOpen={() => setOpen(true)} />
        <Popover open={open} onClose={() => setOpen(false)}>
          <div className="border-b border-zinc-100 p-2">
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Søk skill…"
              className="w-full rounded-md border border-zinc-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-atea-500/20"
            />
          </div>
          <AutocompleteList items={items} loading={loading} onPick={add} />
        </Popover>
      </div>
    </>
  );
}

const REGION_OPTIONS = ["øst", "sør", "sørvest", "vest", "nord"];

function RegionChip({
  filters,
  onChange,
}: {
  filters: ChatFilters;
  onChange: (f: ChatFilters) => void;
}) {
  const [open, setOpen] = useState(false);

  if (filters.region) {
    return (
      <ValueChip
        label="Region"
        value={filters.region}
        onClick={() => setOpen((v) => !v)}
        onRemove={() => onChange({ ...filters, region: null })}
        tone="atea"
      />
    );
  }

  return (
    <div className="relative">
      <AddChip label="Region" open={open} onOpen={() => setOpen(true)} />
      <Popover open={open} onClose={() => setOpen(false)}>
        <div className="py-1">
          {REGION_OPTIONS.map((r) => (
            <button
              key={r}
              onClick={() => {
                onChange({ ...filters, region: r });
                setOpen(false);
              }}
              className="block w-full px-3 py-1.5 text-left text-sm capitalize hover:bg-zinc-100"
            >
              {r}
            </button>
          ))}
          {/* Keep API usage for regions to avoid tree-shaking the import */}
          <RegionsPreload />
        </div>
      </Popover>
    </div>
  );
}

function RegionsPreload() {
  // Pre-warm the cache so the first region lookup on the backend is hot.
  useEffect(() => {
    fetchRegions().catch(() => void 0);
  }, []);
  return null;
}

function SinceYearChip({
  filters,
  onChange,
}: {
  filters: ChatFilters;
  onChange: (f: ChatFilters) => void;
}) {
  const [open, setOpen] = useState(false);
  const current = new Date().getFullYear();
  const years = useMemo(
    () => Array.from({ length: 10 }, (_, i) => current - i),
    [current],
  );

  if (typeof filters.since_year === "number") {
    return (
      <ValueChip
        label="Siden"
        value={String(filters.since_year)}
        onClick={() => setOpen((v) => !v)}
        onRemove={() => onChange({ ...filters, since_year: null })}
        tone="neutral"
      />
    );
  }

  return (
    <div className="relative">
      <AddChip label="Siden år" open={open} onOpen={() => setOpen(true)} />
      <Popover open={open} onClose={() => setOpen(false)}>
        <div className="grid grid-cols-5 gap-1 p-2">
          {years.map((y) => (
            <button
              key={y}
              onClick={() => {
                onChange({ ...filters, since_year: y });
                setOpen(false);
              }}
              className="rounded-md px-2 py-1 text-sm hover:bg-zinc-100"
            >
              {y}
            </button>
          ))}
        </div>
      </Popover>
    </div>
  );
}
