import { motion } from "framer-motion";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { formatPercent } from "@/lib/format";
import { cardHover, fadeUp } from "@/lib/motion";
import type { HealthMetrics } from "@/types/dashboard";

interface RecoveryHealthPanelProps {
  health: HealthMetrics;
}

const CELLS: Array<{
  key: string;
  label: string;
  tone: string;
  value: (health: HealthMetrics) => string;
  hint: (health: HealthMetrics) => string;
}> = [
  {
    key: "success",
    label: "Revenue Recovery Rate",
    tone: "text-recovered",
    value: (health) => formatPercent(health.recovery_success_rate),
    hint: () => "Recovered ₹ ÷ at risk",
  },
  {
    key: "waiting",
    label: "Cases waiting",
    tone: "text-waiting",
    value: (health) => String(health.cases_waiting),
    hint: (health) => formatPercent(health.cases_waiting_share),
  },
  {
    key: "escalated",
    label: "Escalated",
    tone: "text-blocked",
    value: (health) => String(health.escalated),
    hint: (health) => formatPercent(health.escalated_share),
  },
  {
    key: "stopped",
    label: "Stopped",
    tone: "text-blocked",
    value: (health) => String(health.stopped),
    hint: (health) => formatPercent(health.stopped_share),
  },
  {
    key: "promise",
    label: "Promise active",
    tone: "text-ai",
    value: (health) => String(health.promise_active),
    hint: (health) => formatPercent(health.promise_active_share),
  },
];

/** Compact recovery-health status grid. */
export function RecoveryHealthPanel({ health }: RecoveryHealthPanelProps) {
  return (
    <motion.section
      {...fadeUp}
      {...cardHover}
      className="rounded-xl border border-border bg-surface p-4 shadow-[var(--shadow-card)]"
    >
      <SectionHeader title="Recovery health" description={`${health.total_cases} cases in the FitLife cohort.`} />
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
        {CELLS.map((cell) => (
          <li
            key={cell.key}
            className="rounded-lg bg-surface-raised px-3 py-2"
            title={cell.key === "success" ? "Merchant metrics: recovered revenue divided by revenue at risk" : undefined}
          >
            <p className="text-[11px] uppercase tracking-wide text-muted">{cell.label}</p>
            <p className={`mt-1 text-lg font-semibold ${cell.tone}`}>{cell.value(health)}</p>
            <p className="text-[11px] text-muted">{cell.hint(health)}</p>
          </li>
        ))}
      </ul>
    </motion.section>
  );
}
