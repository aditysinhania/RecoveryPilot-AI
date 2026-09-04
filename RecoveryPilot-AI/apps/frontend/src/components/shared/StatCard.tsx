import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { useCountUp } from "@/hooks/useCountUp";
import { cardHover, fadeUp } from "@/lib/motion";

export type StatTone = "recovered" | "waiting" | "blocked" | "ai" | "info";

const TONE: Record<StatTone, string> = {
  recovered: "text-recovered",
  waiting: "text-waiting",
  blocked: "text-blocked",
  ai: "text-ai",
  info: "text-info",
};

interface StatCardProps {
  label: string;
  value: number;
  format: (n: number) => string;
  hint?: string;
  tone?: StatTone;
  icon?: ReactNode;
}

/** KPI tile with a short count-up animation. */
export function StatCard({
  label,
  value,
  format,
  hint,
  tone = "info",
  icon,
}: StatCardProps) {
  const animated = useCountUp(value);
  return (
    <motion.article
      {...fadeUp}
      {...cardHover}
      className="rounded-xl border border-border bg-surface p-3 shadow-[var(--shadow-card)]"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
        {icon ? <span className={`${TONE[tone]}`}>{icon}</span> : null}
      </div>
      <p
        className={`mt-2 text-2xl font-semibold tracking-tight ${TONE[tone]}`}
        aria-label={format(value)}
      >
        {format(animated)}
      </p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </motion.article>
  );
}
