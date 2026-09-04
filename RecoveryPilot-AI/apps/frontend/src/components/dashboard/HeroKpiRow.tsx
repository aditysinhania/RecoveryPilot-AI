import { Clock, IndianRupee, Sparkles, TrendingUp, Users, Wallet } from "lucide-react";
import { StatCard } from "@/components/shared/StatCard";
import { formatPaise, formatPercent } from "@/lib/format";
import type { DashboardView } from "@/types/dashboard";

interface HeroKpiRowProps {
  kpis: DashboardView["kpis"];
}

/** Top KPI strip for the merchant dashboard. */
export function HeroKpiRow({ kpis }: HeroKpiRowProps) {
  return (
    <section aria-label="Key metrics" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      <StatCard
        label="Revenue at risk"
        value={kpis.revenue_at_risk}
        format={formatPaise}
        tone="info"
        icon={<IndianRupee size={16} />}
      />
      <StatCard
        label="Recovered by AI"
        value={kpis.recovered_by_ai}
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
        icon={<Clock size={16} />}
      />
      <StatCard
        label="Cases waiting"
        value={kpis.cases_waiting}
        format={(n) => String(Math.round(n))}
        tone="waiting"
        icon={<Users size={16} />}
      />
    </section>
  );
}
