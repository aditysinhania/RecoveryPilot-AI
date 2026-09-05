import { useEffect, useRef } from "react";
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
import { EmptyWorkspace } from "@/components/workspace/EmptyWorkspace";
import { useMerchantDashboard } from "@/hooks/useMerchantDashboard";
import { FITLIFE_LIST_ID } from "@/services/dashboard";
import { useToast } from "@/toast/ToastProvider";
import { useOutletContext } from "react-router-dom";

type DashboardContext = ReturnType<typeof useMerchantDashboard>;

/** Merchant operations home. */
export default function Dashboard() {
  const ctx = useOutletContext<DashboardContext>();
  const toast = useToast();
  const liveWarned = useRef(false);
  const demoWarned = useRef(false);
  const { view, isLoading, isError, refetch, trendRange, setTrendRange, isFetching, emptyWorkspace, isDemo, setMerchantId } =
    ctx;

  useEffect(() => {
    if (isError && !liveWarned.current) {
      liveWarned.current = true;
      toast.warning("Live API unavailable", "Showing the FitLife seed-42 simulator snapshot.");
    }
  }, [isError, toast]);

  useEffect(() => {
    if (isDemo && !demoWarned.current) {
      demoWarned.current = true;
      toast.warning("Running simulator data", "Demo workspace is pinned to FitLife seed-42.");
    }
  }, [isDemo, toast]);

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (emptyWorkspace) {
    return <EmptyWorkspace onImportDemo={() => setMerchantId(FITLIFE_LIST_ID)} />;
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
