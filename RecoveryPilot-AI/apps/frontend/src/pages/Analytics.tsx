import { AnalyticsInsights } from "@/components/analytics/AnalyticsInsights";
import { AnalyticsKpiRow } from "@/components/analytics/AnalyticsKpiRow";
import { AiBaselineChart } from "@/components/analytics/AiBaselineChart";
import { BankDowntimeChart } from "@/components/analytics/BankDowntimeChart";
import { CalendarImpactChart } from "@/components/analytics/CalendarImpactChart";
import { DiagnosisStackedChart } from "@/components/analytics/DiagnosisStackedChart";
import { MixBarChart } from "@/components/analytics/MixBarChart";
import { OpportunitiesTable } from "@/components/analytics/OpportunitiesTable";
import { PaymentMethodChart } from "@/components/analytics/PaymentMethodChart";
import { PromiseCard } from "@/components/analytics/PromiseCard";
import { RangeToggle } from "@/components/analytics/RangeToggle";
import { StrategyChart } from "@/components/analytics/StrategyChart";
import { RecoveryFunnelChart } from "@/components/charts/RecoveryFunnelChart";
import { RevenueTrendChart } from "@/components/charts/RevenueTrendChart";
import { ErrorState } from "@/components/shared/EmptyState";
import { DashboardSkeleton } from "@/components/shared/LoadingSkeleton";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { useAnalytics } from "@/hooks/useAnalytics";

/** Merchant analytics. Read-only. Uses existing dashboard + queue APIs. */
export default function Analytics() {
  const { model, range, setRange, isLoading, isError, isFetching, refetch } = useAnalytics();

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-base font-semibold tracking-tight">Analytics</h1>
          <p className="text-[11px] text-muted">
            {range}-day charts over the FitLife 90-day window. KPIs are the full cohort.
            {model.sample_size ? ` Queue sample n=${model.sample_size}.` : ""}
          </p>
        </div>
        <RangeToggle range={range} onChange={setRange} />
      </div>
      {isFetching ? (
        <p className="text-xs text-muted" aria-live="polite">
          Refreshing live APIs…
        </p>
      ) : null}
      {isError ? (
        <ErrorState
          compact
          message="Live APIs are unavailable. Showing the FitLife seed-42 simulator snapshot."
          onRetry={() => refetch()}
        />
      ) : null}

      <AnalyticsKpiRow kpis={model.kpis} />

      <SectionHeader title="Recovery performance" description="Diagnosis, planner, baseline, and funnel." />
      <div className="grid gap-4 lg:grid-cols-2">
        <DiagnosisStackedChart data={model.diagnosis_stack} sampleLabel={model.sample_label} />
        <StrategyChart data={model.strategies} />
        <AiBaselineChart baseline={model.baseline} />
        <RecoveryFunnelChart data={model.funnel} />
      </div>

      <SectionHeader title="Customer insights" description="Segment, plan, promises, and still-open value." />
      <div className="grid gap-4 lg:grid-cols-2">
        <MixBarChart
          title="Recovery by customer segment"
          description="Recovered rupees in the loaded queue, grouped by persona."
          data={model.segments}
        />
        <MixBarChart
          title="Recovery by subscription plan"
          description="Recovered rupees by FitLife plan, mapped from invoice amount."
          data={model.plans}
        />
        <PromiseCard stats={model.promises} />
        <OpportunitiesTable rows={model.opportunities} />
      </div>

      <SectionHeader title="Operational insights" description="Rails, daily captures, downtime, and calendar." />
      <div className="grid gap-4 lg:grid-cols-2">
        <PaymentMethodChart data={model.payment_methods} />
        <RevenueTrendChart
          data={model.trend}
          range={range}
          onRangeChange={setRange}
          ranges={[7, 30, 90]}
          showRangeToggle={false}
        />
        <BankDowntimeChart bank={model.bank} />
        <CalendarImpactChart calendar={model.calendar} festivals={model.festivals} />
      </div>

      <SectionHeader title="AI insights" description="Fallback Gemini-shaped cards. No Gemini HTTP call." />
      <AnalyticsInsights model={model} />
    </div>
  );
}
