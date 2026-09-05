import { AiInsightsPanel } from "@/components/ai/AiInsightsPanel";
import { FailureReasonsChart } from "@/components/charts/FailureReasonsChart";
import { RecoveryFunnelChart } from "@/components/charts/RecoveryFunnelChart";
import { RevenueTrendChart } from "@/components/charts/RevenueTrendChart";
import { AiLiftCard } from "@/components/dashboard/AiLiftCard";
import { HeroKpiRow } from "@/components/dashboard/HeroKpiRow";
import { OrchestratorKpiRow } from "@/components/dashboard/OrchestratorKpiRow";
import { RecentActivity } from "@/components/dashboard/RecentActivity";
import { RecoveryHealthPanel } from "@/components/dashboard/RecoveryHealthPanel";
import { TopCustomersTable } from "@/components/dashboard/TopCustomersTable";
import { ErrorState } from "@/components/shared/EmptyState";
import { DashboardSkeleton } from "@/components/shared/LoadingSkeleton";
import { useMerchantDashboard } from "@/hooks/useMerchantDashboard";
import { useOutletContext } from "react-router-dom";

type DashboardContext = ReturnType<typeof useMerchantDashboard>;

/** Merchant operations home. */
export default function Dashboard() {
  const ctx = useOutletContext<DashboardContext>();
  const { view, isLoading, isError, refetch, trendRange, setTrendRange, isFetching } = ctx;

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-4">
      {isFetching ? (
        <p className="text-xs text-muted" aria-live="polite">
          Refreshing live APIs…
        </p>
      ) : null}
      {isError ? (
        <ErrorState
          message="Live APIs are unavailable. Showing the FitLife seed-42 simulator snapshot."
          onRetry={() => {
            void refetch();
          }}
        />
      ) : null}
      <HeroKpiRow kpis={view.kpis} />
      <OrchestratorKpiRow orchestrator={view.orchestrator} />
      <AiInsightsPanel insights={view.insights} />
      <div className="grid gap-4 lg:grid-cols-2">
        <RecoveryFunnelChart data={view.funnel} />
        <FailureReasonsChart data={view.failureReasons} />
      </div>
      <RevenueTrendChart data={view.trend} range={trendRange} onRangeChange={setTrendRange} />
      <div className="grid gap-4 xl:grid-cols-2">
        <AiLiftCard lift={view.lift} />
        <RecoveryHealthPanel health={view.health} />
      </div>
      <RecentActivity items={view.activity} />
      <TopCustomersTable rows={view.topCustomers} />
    </div>
  );
}
