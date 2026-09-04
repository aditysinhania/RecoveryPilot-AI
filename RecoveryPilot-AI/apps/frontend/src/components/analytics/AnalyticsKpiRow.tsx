import { IndianRupee, ShieldCheck, Sparkles, TrendingUp, Wallet } from "lucide-react";
import { StatCard } from "@/components/shared/StatCard";
import { formatPaise, formatPercent } from "@/lib/format";
import type { AnalyticsView } from "@/types/analytics";

interface AnalyticsKpiRowProps {
  kpis: AnalyticsView["kpis"];
}

/** Cohort KPI strip for the analytics page. */
export function AnalyticsKpiRow({ kpis }: AnalyticsKpiRowProps) {
  return (
    <section aria-label="Analytics KPIs" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      <StatCard
        label="Revenue at risk"
        value={kpis.revenue_at_risk}
        format={formatPaise}
        tone="info"
        icon={<IndianRupee size={16} />}
      />
      <StatCard
        label="Revenue recovered"
        value={kpis.recovered_revenue}
        format={formatPaise}
        tone="recovered"
        icon={<Wallet size={16} />}
      />
      <StatCard
        label="Recovery rate"
        value={kpis.recovery_rate}
        format={(n) => formatPercent(n)}
        tone="recovered"
        icon={<TrendingUp size={16} />}
      />
      <StatCard
        label="AI lift vs baseline"
        value={kpis.ai_lift}
        format={formatPaise}
        tone="ai"
        icon={<Sparkles size={16} />}
      />
      <StatCard
        label="Pending recovery value"
        value={kpis.pending_recovery_value}
        format={formatPaise}
        tone="waiting"
        icon={<IndianRupee size={16} />}
      />
      <StatCard
        label="Harmful retries prevented"
        value={kpis.harmful_retries_prevented}
        format={(n) => String(Math.round(n))}
        tone="ai"
        icon={<ShieldCheck size={16} />}
      />
    </section>
  );
}
