import { Ban, GitBranch, History, ShieldCheck, Webhook } from "lucide-react";
import { StatCard } from "@/components/shared/StatCard";
import type { AuditKpis } from "@/types/audit";

interface AuditMetricsHeaderProps {
  kpis: AuditKpis;
}

function count(value: number): string {
  return Math.round(value).toLocaleString("en-IN");
}

/** Cohort KPI strip for the audit explorer. */
export function AuditMetricsHeader({ kpis }: AuditMetricsHeaderProps) {
  return (
    <section aria-label="Audit KPIs" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      <StatCard label="Audit events" value={kpis.audit_events} format={count} tone="info" icon={<History size={16} />} />
      <StatCard
        label="Correlation replays"
        value={kpis.correlation_replays}
        format={count}
        tone="ai"
        icon={<GitBranch size={16} />}
      />
      <StatCard label="Policy stops" value={kpis.policy_stops} format={count} tone="blocked" icon={<Ban size={16} />} />
      <StatCard
        label="Webhook replays"
        value={kpis.webhook_replays}
        format={count}
        tone="info"
        icon={<Webhook size={16} />}
      />
      <StatCard
        label="Duplicate events prevented"
        value={kpis.duplicates_prevented}
        format={count}
        tone="ai"
        icon={<ShieldCheck size={16} />}
      />
    </section>
  );
}
