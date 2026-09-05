import type { MixRow, PaymentMixRow, StatusStackRow, StrategyRow } from "@/types/analytics";
import type { DashboardInsight, FunnelStage, TrendPoint } from "@/types/dashboard";

export const MERCHANT_KEYS = ["gym", "saas", "ott", "edtech"] as const;
export const BASELINE_STRATEGIES = ["immediate_retry", "wait_three_days", "payday_only"] as const;
export const SIMULATOR_SEEDS = [42, 7, 99, 2026, 314] as const;

export type MerchantKey = (typeof MERCHANT_KEYS)[number];
export type BaselineStrategy = (typeof BASELINE_STRATEGIES)[number];

export interface MerchantProfileView {
  key: MerchantKey;
  label: string;
  merchant_name: string;
  business_category: string;
  notes: string;
  arpu_paise: number;
  festival_default: boolean;
  method_weights: Record<string, number>;
  segment_weights: Record<string, number>;
}

export interface ScenarioControls {
  merchant: MerchantKey;
  customerCount: number;
  failureRate: number;
  salaryCycle: boolean;
  festivalCalendar: boolean;
  bankDowntime: boolean;
  promiseToPay: boolean;
  baselineStrategy: BaselineStrategy;
  seed: number;
}

export interface LabKpis {
  revenue_at_risk: number;
  revenue_recovered: number;
  recovery_rate: number;
  ai_lift: number;
  harmful_retries_prevented: number;
  compliance_savings: number;
  communication_cost: number;
}

export interface ScenarioResult {
  id: string;
  controls: ScenarioControls;
  label: string;
  generated_at: string;
  source: "snapshot" | "scenario";
  cases: number;
  customers: number;
  ai: LabKpis;
  baseline: LabKpis;
  funnel_ai: FunnelStage[];
  funnel_baseline: FunnelStage[];
  diagnosis: StatusStackRow[];
  strategies: StrategyRow[];
  segments: MixRow[];
  methods: PaymentMixRow[];
  trend: TrendPoint[];
  insights: DashboardInsight[];
}

export interface SavedScenario {
  id: string;
  name: string;
  saved_at: string;
  controls: ScenarioControls;
  result: ScenarioResult;
}

export interface ScenarioDelta {
  key: keyof LabKpis;
  label: string;
  ai: number;
  baseline: number;
  delta: number;
  kind: "paise" | "rate" | "count";
  higher_is_better: boolean;
}
