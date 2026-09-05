import { formatPercent } from "@/lib/format";
import type { ComplianceInsights } from "@/types/audit";

interface ComplianceInsightsCardProps {
  insights: ComplianceInsights;
}

function Chip({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface px-2.5 py-1.5">
      <p className="text-[10px] uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-0.5 text-sm font-semibold tabular-nums ${tone}`}>{value}</p>
    </div>
  );
}

/** Compact compliance chips. Replaces the large empty chart panel. */
export function ComplianceInsightsCard({ insights }: ComplianceInsightsCardProps) {
  return (
    <section aria-label="Compliance insights" className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-6">
      <Chip label="Allow" value={String(insights.allow)} tone="text-recovered" />
      <Chip label="Stop" value={String(insights.stop)} tone="text-blocked" />
      <Chip label="STOP vs ALLOW" value={formatPercent(insights.stop_allow_ratio)} tone="text-foreground" />
      <Chip label="Escalations" value={String(insights.escalations)} tone="text-blocked" />
      <Chip label="Duplicates" value={String(insights.duplicates_prevented)} tone="text-ai" />
      <Chip label="Idempotency keys" value={String(insights.idempotency_keys)} tone="text-info" />
    </section>
  );
}
