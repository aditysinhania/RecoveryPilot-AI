import { motion } from "framer-motion";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { formatPaise, formatPercent } from "@/lib/format";
import { cardHover, fadeUp } from "@/lib/motion";
import type { AiLift } from "@/types/dashboard";

interface AiLiftCardProps {
  lift: AiLift;
}

/** Compact two-column AI vs baseline comparison. */
export function AiLiftCard({ lift }: AiLiftCardProps) {
  const total = Math.max(lift.recovered_by_ai, 1);
  const aiShare = Math.min(1, lift.recovered_by_ai / total);
  const baseShare = Math.min(1, lift.recovered_by_baseline / total);
  const commsSaved = lift.communication_cost_saved;
  return (
    <motion.section
      {...fadeUp}
      {...cardHover}
      className="rounded-xl border border-border bg-surface p-4 shadow-[var(--shadow-card)]"
    >
      <SectionHeader
        title="AI lift"
        description="RecoveryPilot versus the immediate-retry baseline."
      />
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted">Recovered by AI</p>
              <p className="mt-1 text-xl font-semibold text-recovered">{formatPaise(lift.recovered_by_ai)}</p>
              <p className="text-[11px] text-muted">{formatPercent(lift.ai_rate)}</p>
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-wide text-muted">Recovered by baseline</p>
              <p className="mt-1 text-xl font-semibold text-muted">{formatPaise(lift.recovered_by_baseline)}</p>
              <p className="text-[11px] text-muted">{formatPercent(lift.baseline_rate)}</p>
            </div>
          </div>
          <div className="mt-3 space-y-1.5" aria-label="Recovery comparison">
            <Progress label="AI" value={aiShare} tone="recovered" />
            <Progress label="Baseline" value={baseShare} tone="muted" />
          </div>
        </div>
        <dl className="grid grid-cols-1 gap-2 sm:grid-cols-3 lg:grid-cols-1">
          <Metric label="Extra revenue recovered" value={formatPaise(lift.extra_revenue)} />
          <Metric label="Harmful retries prevented" value={String(lift.harmful_retries_prevented)} />
          <Metric
            label={commsSaved >= 0 ? "Communication cost saved" : "Outreach vs SMS blast"}
            value={
              commsSaved >= 0
                ? formatPaise(commsSaved, true)
                : `${formatPaise(lift.ai_outreach_paise, true)} AI · ${formatPaise(lift.baseline_outreach_paise, true)} baseline`
            }
          />
        </dl>
      </div>
    </motion.section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-surface-raised px-3 py-2">
      <dt className="text-[11px] uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm font-semibold text-foreground">{value}</dd>
    </div>
  );
}

function Progress({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "recovered" | "muted";
}) {
  const bar = tone === "recovered" ? "bg-recovered" : "bg-zinc-600";
  return (
    <div>
      <div className="mb-0.5 flex justify-between text-[11px] text-muted">
        <span>{label}</span>
        <span>{Math.round(value * 100)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-hover">
        <div className={`h-full rounded-full ${bar}`} style={{ width: `${value * 100}%` }} />
      </div>
    </div>
  );
}
