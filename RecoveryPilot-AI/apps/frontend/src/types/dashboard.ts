export type ExplanationSource = "gemini" | "fallback";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type TrendRange = 7 | 30 | 90;

export interface MerchantOption {
  id: string;
  merchant_name: string;
  business_category: string;
  timezone: string;
}

export interface MerchantMetrics {
  merchant_id: string;
  revenue_at_risk: number;
  recovered_revenue: number;
  suppressed_revenue: number;
  recovery_rate: number;
  escalation_count: number;
  policy_stop_count: number;
  updated_at: string | null;
}

export interface MerchantSummary {
  merchant: MerchantOption & {
    email?: string;
    phone?: string;
  };
  customers: number;
  subscriptions: number;
  payments: number;
  failed_payments: number;
  recovery_cases: number;
  metrics: MerchantMetrics;
}

export interface RecoverySummary {
  open_cases: number;
  recovered_cases: number;
  stopped_cases: number;
  escalated_cases: number;
  waiting_retry: number;
  waiting_promise: number;
  total_revenue_at_risk: number;
  recovered_revenue: number;
  recovery_rate: number;
  pending_recovery_value?: number;
  closed_cases?: number;
}

export interface FunnelStage {
  stage: string;
  count: number;
  revenue_paise: number;
}

export interface FailureReasonSlice {
  key: string;
  label: string;
  count: number;
  revenue_paise: number;
}

export interface TrendPoint {
  date: string;
  recovered_paise: number;
  recovered_count: number;
  baseline_paise: number;
}

export interface HealthMetrics {
  recovery_success_rate: number;
  cases_waiting: number;
  cases_waiting_share: number;
  escalated: number;
  escalated_share: number;
  stopped: number;
  stopped_share: number;
  promise_active: number;
  promise_active_share: number;
  total_cases: number;
}

export interface TopCustomerRow {
  recovery_case_id: string;
  customer_name: string;
  customer_segment: string;
  plan_name: string;
  amount: number;
  diagnosis: string;
  strategy: string;
  recovery_status: string;
  priority_score: number;
  failed_at?: string | null;
}

export interface ActivityItem {
  event_type: string;
  summary: string;
  timestamp: string;
  actor: string;
  recovery_case_id?: string | null;
}

export interface DashboardInsight {
  title: string;
  summary: string;
  risk_level: string;
  next_action: string;
  source: ExplanationSource;
  cached: boolean;
  generated_at: string;
}

export interface AiLift {
  recovered_by_ai: number;
  recovered_by_baseline: number;
  extra_revenue: number;
  harmful_retries_prevented: number;
  communication_cost_saved: number;
  ai_outreach_paise: number;
  baseline_outreach_paise: number;
  ai_rate: number;
  baseline_rate: number;
}

export interface DashboardView {
  merchant: MerchantOption;
  environment: string;
  dataSource: "live" | "simulator";
  lastSyncedAt: string;
  kpis: {
    revenue_at_risk: number;
    recovered_by_ai: number;
    recovery_rate: number;
    ai_lift: number;
    pending_recovery_value: number;
    cases_waiting: number;
  };
  funnel: FunnelStage[];
  trend: TrendPoint[];
  failureReasons: FailureReasonSlice[];
  lift: AiLift;
  health: HealthMetrics;
  insights: DashboardInsight[];
  activity: ActivityItem[];
  topCustomers: TopCustomerRow[];
}

export interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
  request_id?: string;
  correlation_id?: string;
  timestamp?: string;
  error?: string;
  code?: string;
}

export interface PaginatedEnvelope<T> extends ApiEnvelope<T[]> {
  page: number;
  page_size: number;
  total: number;
  total_records: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface RecoveryQueueItem {
  recovery_case_id: string;
  merchant_id: string;
  customer_id: string;
  payment_id: string;
  customer_name: string;
  customer_segment: string;
  amount: number;
  currency: string;
  payment_method?: string | null;
  failure_reason?: string | null;
  diagnosed_reason?: string | null;
  recovery_status: string;
  priority_score?: number | null;
  ai_confidence?: number | null;
  payment_due_date?: string | null;
  failed_at: string;
  recovery_started_at?: string | null;
}

export interface PaymentListItem {
  id: string;
  amount: number;
  payment_status: string;
  failure_reason?: string | null;
  paid_at?: string | null;
  payment_time?: string | null;
  created_at: string;
  plan_name?: string | null;
}

export interface AuditEventItem {
  event_id?: string | null;
  recovery_case_id?: string | null;
  event_type: string;
  actor: string;
  timestamp: string;
  summary: string;
}

export interface FitlifeSnapshot {
  seed: number;
  as_of: string;
  source: string;
  merchant: MerchantOption & {
    list_id: string;
    email: string;
    phone: string;
  };
  counts: {
    customers: number;
    subscriptions: number;
    payments: number;
    failed_payments: number;
    recovery_cases: number;
  };
  metrics: Omit<MerchantMetrics, "merchant_id"> & { updated_at: string };
  baseline: {
    recovered_count: number;
    recovered_revenue: number;
    harmful_retries: number;
    recovery_rate: number;
  };
  lift_recovered_revenue: number;
  harmful_retries_prevented: number;
  communication_cost_saved: number;
  communication_costs: {
    ai_total_paise: number;
    baseline_total_paise: number;
    saved_paise: number;
  };
  recovery_summary: RecoverySummary;
  funnel: FunnelStage[];
  failure_reasons: FailureReasonSlice[];
  trend: TrendPoint[];
  health: HealthMetrics;
  top_customers: TopCustomerRow[];
  activity: ActivityItem[];
}
