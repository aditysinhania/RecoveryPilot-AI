import type { AnalyticsRange } from "@/types/analytics";

interface RangeToggleProps {
  range: AnalyticsRange;
  onChange: (range: AnalyticsRange) => void;
}

/** 7 / 30 / 90 day window over the FitLife observation period. */
export function RangeToggle({ range, onChange }: RangeToggleProps) {
  return (
    <div className="flex rounded-lg border border-border p-0.5" role="group" aria-label="Analytics range">
      {([7, 30, 90] as AnalyticsRange[]).map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={`rounded-md px-2.5 py-1 text-xs ${
            range === option ? "bg-surface-hover text-foreground" : "text-muted"
          }`}
          aria-pressed={range === option}
        >
          {option}d
        </button>
      ))}
    </div>
  );
}
