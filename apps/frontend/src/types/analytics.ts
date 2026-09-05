import type { DashboardInsight, FailureReasonSlice, FunnelStage, TrendPoint, TrendRange } from "@/types/dashboard";

export type AnalyticsRange = TrendRange;

export interface StatusStackRow {
  key: string;
  label: string;
  recovered: number;
  waiting: number;
  escalated: number;
  stopped: number;
  open: number;
  revenue_paise: number;
}

export interface StrategyRow {
  key: string;
  label: string;
  recovered: number;
  remaining: number;
  recovered_paise: number;
  rate: number;
}

export interface MixRow {
  key: string;
  label: string;
  count: number;
  recovered: number;
  revenue_paise: number;
  recovered_paise: number;
}

export interface PaymentMixRow {
  key: string;
  label: string;
  recovered: number;
  failed: number;
  revenue_paise: number;
}

export interface OpportunityRow {
  recovery_case_id: string;
  customer_name: string;
  plan_name: string;
  diagnosis: string;
  strategy: string;
  amount: number;
  expected_paise: number;
  recovery_status: string;
}

export interface PromiseStats {
  active: number;
  recovered: number;
  rate: number;
  sample_size: number;
}

export interface CalendarBucket {
  key: string;
  label: string;
  recovered_paise: number;
  recovered_count: number;
}

export interface FestivalImpactRow {
  date: string;
  name: string;
  effect: string;
  applied: boolean;
  recovered_paise: number;
  typical_paise: number;
}

export interface AnalyticsView {
  range: AnalyticsRange;
  sample_size: number;
  sample_label: string;
  kpis: {
    revenue_at_risk: number;
    recovered_revenue: number;
    recovery_rate: number;
    ai_lift: number;
    pending_recovery_value: number;
    harmful_retries_prevented: number;
  };
  diagnosis_stack: StatusStackRow[];
  strategies: StrategyRow[];
  baseline: {
    ai_recovered: number;
    baseline_recovered: number;
    ai_rate: number;
    baseline_rate: number;
  };
  funnel: FunnelStage[];
  segments: MixRow[];
  plans: MixRow[];
  promises: PromiseStats;
  opportunities: OpportunityRow[];
  payment_methods: PaymentMixRow[];
  trend: TrendPoint[];
  bank: {
    cases: number;
    revenue_paise: number;
    share: number;
    sample_rate: number;
    other_rate: number;
  };
  calendar: CalendarBucket[];
  festivals: FestivalImpactRow[];
  compliance: {
    stopped_cases: number;
    suppressed_revenue: number;
    harmful_retries_prevented: number;
  };
  loss_leaders: FailureReasonSlice[];
  insights: DashboardInsight[];
}
