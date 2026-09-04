import { formatDateTime, formatPaise, formatPercent, titleCase } from "@/lib/format";
import type { CaseDrawerModel } from "@/types/recovery";

interface PlannerCardProps {
  planner: CaseDrawerModel["planner"];
}

/** Planned recovery strategy, schedule, probability, and expected value. */
export function PlannerCard({ planner }: PlannerCardProps) {
  const pct = Math.round(planner.recovery_probability * 100);
  const bar = planner.recovery_probability >= 0.75 ? "bg-recovered" : planner.recovery_probability >= 0.5 ? "bg-waiting" : "bg-blocked";
  return (
    <section className="rounded-xl border border-border bg-surface-raised p-4" aria-labelledby="planner-heading">
      <h3 id="planner-heading" className="text-[11px] font-semibold uppercase tracking-wide text-muted">
        Planner
      </h3>
      <p className="mt-1 text-sm font-medium text-foreground">{titleCase(planner.primary_strategy)}</p>
      <p className="mt-1 text-xs text-muted">
        Fallback <span className="text-foreground">{titleCase(planner.fallback_strategy)}</span>
      </p>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-xs">
        <div>
          <dt className="text-muted">Scheduled execution</dt>
          <dd className="mt-0.5">{planner.scheduled_time ? formatDateTime(planner.scheduled_time) : "—"}</dd>
        </div>
        <div>
          <dt className="text-muted">Est. comms cost</dt>
          <dd className="mt-0.5 tabular-nums">{formatPaise(planner.estimated_communication_cost, true)}</dd>
        </div>
        <div className="col-span-2">
          <div className="flex items-center justify-between gap-2">
            <dt className="text-muted">Recovery probability</dt>
            <dd className="tabular-nums font-medium">{formatPercent(planner.recovery_probability, 0)}</dd>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-zinc-800" aria-hidden>
            <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
          </div>
        </div>
        <div className="col-span-2 rounded-lg border border-recovered/20 bg-recovered-muted/40 px-3 py-2">
          <dt className="text-[11px] uppercase tracking-wide text-muted">Expected recovered</dt>
          <dd className="mt-0.5 text-sm font-semibold tabular-nums text-recovered">
            {formatPaise(planner.expected_recovered_value)}
          </dd>
        </div>
      </dl>
    </section>
  );
}
