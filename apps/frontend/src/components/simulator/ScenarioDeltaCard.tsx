import { formatPaise, formatPercent } from "@/lib/format";
import type { ScenarioDelta } from "@/types/simulatorLab";

interface ScenarioDeltaCardProps {
  row: ScenarioDelta;
  leftLabel?: string;
  rightLabel?: string;
}

function formatValue(row: ScenarioDelta, value: number): string {
  if (row.kind === "rate") {
    return formatPercent(value);
  }
  if (row.kind === "count") {
    return Math.round(value).toLocaleString("en-IN");
  }
  return formatPaise(value);
}

/** One metric delta row used in the comparison drawer. */
export function ScenarioDeltaCard({
  row,
  leftLabel = "Current",
  rightLabel = "Seed 42",
}: ScenarioDeltaCardProps) {
  const positive = row.higher_is_better ? row.delta > 0 : row.delta < 0;
  const tone = row.delta === 0 ? "text-muted" : positive ? "text-recovered" : "text-blocked";
  const sign = row.delta > 0 ? "+" : "";
  const deltaText =
    row.kind === "rate"
      ? `${sign}${formatPercent(row.delta)}`
      : row.kind === "count"
        ? `${sign}${Math.round(row.delta).toLocaleString("en-IN")}`
        : `${sign}${formatPaise(row.delta)}`;
  return (
    <article className="rounded-lg border border-border bg-canvas px-2.5 py-2">
      <p className="text-[10px] font-medium uppercase tracking-wide text-muted">{row.label}</p>
      <div className="mt-1 grid grid-cols-3 gap-2 text-xs">
        <div>
          <p className="text-zinc-500">{leftLabel}</p>
          <p className="tabular-nums text-foreground">{formatValue(row, row.ai)}</p>
        </div>
        <div>
          <p className="text-zinc-500">{rightLabel}</p>
          <p className="tabular-nums text-foreground">{formatValue(row, row.baseline)}</p>
        </div>
        <div className="text-right">
          <p className="text-zinc-500">Delta</p>
          <p className={`tabular-nums font-semibold ${tone}`}>{deltaText}</p>
        </div>
      </div>
    </article>
  );
}
