import { motion } from "framer-motion";
import { useCountUp } from "@/hooks/useCountUp";
import { fadeUp } from "@/lib/motion";
import { formatPaise, formatPercent } from "@/lib/format";
import { kpiDeltas } from "@/lib/simulatorLab";
import type { LabKpis, ScenarioDelta } from "@/types/simulatorLab";

interface KPIComparisonGridProps {
  ai: LabKpis;
  baseline: LabKpis;
}

function formatDelta(row: ScenarioDelta): string {
  const sign = row.delta > 0 ? "+" : "";
  if (row.kind === "rate") {
    return `${sign}${formatPercent(row.delta)}`;
  }
  if (row.kind === "count") {
    return `${sign}${Math.round(row.delta).toLocaleString("en-IN")}`;
  }
  return `${sign}${formatPaise(row.delta)}`;
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

function deltaTone(row: ScenarioDelta): string {
  if (row.delta === 0) {
    return "text-muted";
  }
  const positive = row.higher_is_better ? row.delta > 0 : row.delta < 0;
  return positive ? "text-recovered" : "text-blocked";
}

function CountCell({ row, value, tone }: { row: ScenarioDelta; value: number; tone: string }) {
  const animated = useCountUp(value);
  return <p className={`text-sm font-semibold tabular-nums ${tone}`}>{formatValue(row, animated)}</p>;
}

/** Two-column RecoveryPilot vs baseline KPIs with green/red deltas. */
export function KPIComparisonGrid({ ai, baseline }: KPIComparisonGridProps) {
  const rows = kpiDeltas(ai, baseline);
  return (
    <motion.section
      {...fadeUp}
      aria-label="Live KPI comparison"
      className="overflow-hidden rounded-xl border border-border bg-surface shadow-[var(--shadow-card)]"
    >
      <div className="grid grid-cols-[1.2fr_1fr_1fr_auto] gap-2 border-b border-border px-3 py-2 text-[10px] font-medium uppercase tracking-wide text-muted">
        <p>Metric</p>
        <p>RecoveryPilot AI</p>
        <p>Baseline</p>
        <p className="text-right">Delta</p>
      </div>
      {rows.map((row) => (
        <div
          key={row.key}
          className="grid grid-cols-[1.2fr_1fr_1fr_auto] items-center gap-2 border-b border-border px-3 py-2 last:border-b-0"
        >
          <p className="text-xs text-foreground">{row.label}</p>
          <CountCell row={row} value={row.ai} tone="text-recovered" />
          <CountCell row={row} value={row.baseline} tone="text-waiting" />
          <p className={`text-right text-xs font-semibold tabular-nums ${deltaTone(row)}`}>{formatDelta(row)}</p>
        </div>
      ))}
    </motion.section>
  );
}
