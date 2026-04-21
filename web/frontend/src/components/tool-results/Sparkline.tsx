/**
 * Tiny bar chart for monthly billing rates. Each value is 0..1-ish (can
 * exceed 1 when over-billed). Height is clamped to 120 % so outliers
 * don't blow the layout.
 */

interface SparklineProps {
  months: Record<string, number | null | undefined>;
  max?: number;
}

const MONTH_SHORT: Record<string, string> = {
  january: "Jan",
  february: "Feb",
  march: "Mar",
  april: "Apr",
  may: "Mai",
  june: "Jun",
  july: "Jul",
  august: "Aug",
  september: "Sep",
  october: "Okt",
  november: "Nov",
  december: "Des",
};

function colorFor(rate: number): string {
  if (rate < 0.5) return "bg-emerald-500";
  if (rate < 0.8) return "bg-amber-400";
  return "bg-rose-500";
}

export default function Sparkline({ months, max = 1.2 }: SparklineProps) {
  const entries = Object.entries(months);
  return (
    <div className="flex items-end gap-1">
      {entries.map(([month, raw]) => {
        const value = typeof raw === "number" && !Number.isNaN(raw) ? raw : null;
        const height = value === null ? 4 : Math.min(value, max) * 60;
        const label = MONTH_SHORT[month.toLowerCase()] ?? month.slice(0, 3);
        return (
          <div key={month} className="flex flex-col items-center gap-1">
            <div
              className={`w-5 rounded-sm ${value === null ? "bg-slate-200" : colorFor(value)}`}
              style={{ height: `${height}px` }}
              title={
                value === null
                  ? "Ingen data"
                  : `${label}: ${Math.round(value * 100)}% fakturert`
              }
            />
            <span className="text-[10px] text-slate-500">{label}</span>
          </div>
        );
      })}
    </div>
  );
}
