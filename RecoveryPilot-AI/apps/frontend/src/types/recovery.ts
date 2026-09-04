export const DIAGNOSIS_VALUES = [
  "INSUFFICIENT_FUNDS",
  "CARD_EXPIRED",
  "UPI_FAILURE",
  "MANDATE_REVOKED",
  "BANK_TIMEOUT",
  "CUSTOMER_CANCELLED",
  "ALREADY_PAID",
  "DISPUTE",
  "UNKNOWN",
] as const;

export const PLANNER_STRATEGIES = [
  "WAIT_FOR_PAYDAY",
  "RETRY_PAYMENT",
  "RETRY_SILENTLY",
  "SEND_PAYMENT_LINK",
  "SWITCH_PAYMENT_METHOD",
  "REQUEST_NEW_MANDATE",
  "HONOUR_PROMISE_TO_PAY",
  "ESCALATE_TO_HUMAN",
  "STOP_RECOVERY",
] as const;

export const POLICY_DECISIONS = ["ALLOW", "DENY", "ESCALATE", "STOP"] as const;

export const RECOVERY_STATUSES = [
  "OPEN",
  "DIAGNOSED",
  "WAITING_RETRY",
  "WAITING_PROMISE",
  "RECOVERED",
  "STOPPED",
  "ESCALATED",
  "CLOSED",
] as const;

export const PRIORITY_BANDS = ["HIGH", "MEDIUM", "LOW"] as const;

export const PAYMENT_METHODS = ["UPI", "CARD", "NETBANKING", "WALLET", "MANDATE"] as const;

export const CUSTOMER_SEGMENTS = [
  "NEW",
  "ACTIVE",
  "LOYAL",
  "AT_RISK",
  "HIGH_VALUE",
  "CHURN_RISK",
] as const;

export type DiagnosisValue = (typeof DIAGNOSIS_VALUES)[number];
export type PlannerStrategy = (typeof PLANNER_STRATEGIES)[number];
export type PolicyDecision = (typeof POLICY_DECISIONS)[number];
export type RecoveryStatus = (typeof RECOVERY_STATUSES)[number];
export type PriorityBand = (typeof PRIORITY_BANDS)[number];
export type PaymentMethod = (typeof PAYMENT_METHODS)[number];
export type CustomerSegment = (typeof CUSTOMER_SEGMENTS)[number];

export type QueueSortKey =
  | "customer_name"
  | "plan_name"
  | "amount"
  | "diagnosed_reason"
  | "planner_strategy"
  | "policy_status"
  | "recovery_status"
  | "priority_score"
  | "last_updated"
  | "ai_confidence";

export interface RecoveryQueueFilters {
  search: string;
  diagnosis: string;
  policy: string;
  strategy: string;
  priority: string;
  status: string;
  amountMin: string;
  amountMax: string;
  paymentMethod: string;
  dateFrom: string;
  dateTo: string;
  segment: string;
  merchantId: string;
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

export interface QueueRow extends RecoveryQueueItem {
  plan_name: string;
  planner_strategy: string;
  policy_status: string;
  last_updated: string;
}

export interface RecoveryQueueSummary {
  open_cases: number;
  recovered_cases: number;
  stopped_cases: number;
  escalated_cases: number;
  waiting_retry: number;
  waiting_promise: number;
  total_revenue_at_risk: number;
  recovered_revenue: number;
  recovery_rate: number;
  recovered_today: number;
}

export interface QueuePage {
  items: QueueRow[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  source: "live" | "simulator";
}

export interface EvidenceItem {
  label: string;
  weight: number;
  message: string;
}

export interface ConfidenceContributor {
  label: string;
  weight: number;
}

export interface CustomerDetail {
  id: string;
  merchant_id: string;
  full_name: string;
  email: string;
  phone: string;
  customer_segment: string;
  preferred_payment_method?: string | null;
  preferred_language: string;
  consent_status: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PaymentDetail {
  id: string;
  merchant_id: string;
  customer_id: string;
  subscription_id?: string | null;
  razorpay_order_id?: string | null;
  razorpay_payment_id?: string | null;
  idempotency_key?: string | null;
  payment_status: string;
  failure_reason?: string | null;
  payment_method?: string | null;
  amount: number;
  currency: string;
  attempt_number: number;
  payment_due_date?: string | null;
  paid_at?: string | null;
  created_at: string;
  updated_at?: string | null;
}

export interface SubscriptionDetail {
  id?: string | null;
  subscription_name: string;
  billing_amount: number;
  billing_frequency: string;
  next_billing_date?: string | null;
  mandate_status: string;
  subscription_status: string;
}

export interface RecoveryActionDetail {
  id: string;
  recovery_case_id: string;
  action_type: string;
  scheduled_time?: string | null;
  executed_time?: string | null;
  execution_status: string;
  razorpay_payment_link?: string | null;
  retry_number: number;
  response_code?: string | null;
  response_message?: string | null;
  action_metadata: Record<string, unknown>;
  created_at?: string | null;
}

export interface PromiseDetail {
  id: string;
  promised_amount: number;
  promised_date: string;
  promise_status: string;
  fulfilled_at?: string | null;
}

export interface RecoveryCaseDetail {
  recovery_case_id: string;
  merchant_id: string;
  recovery_status: string;
  diagnosed_reason?: string | null;
  diagnosis_model?: string | null;
  diagnosis_version?: string | null;
  ai_confidence?: number | null;
  priority_score?: number | null;
  recovery_started_at?: string | null;
  recovery_completed_at?: string | null;
  created_at: string;
  updated_at: string;
  customer: CustomerDetail;
  payment: PaymentDetail;
  subscription: SubscriptionDetail | null;
  latest_action: RecoveryActionDetail | null;
  promise_to_pay: PromiseDetail | null;
  promise_status?: string | null;
}

export interface PolicyRow {
  recovery_case_id: string;
  event_id?: string | null;
  policy_name: string;
  decision: string;
  reason: string;
  evaluated_at: string;
}

export interface EvaluatedRuleRow {
  policy_name: string;
  result: string;
  reason: string;
}

export interface TimelineEvent {
  event_type: string;
  occurred_at: string;
  summary: string;
  source: string;
  reference_id?: string | null;
  details: Record<string, unknown>;
}

export interface AuditEvent {
  event_id?: string | null;
  recovery_case_id?: string | null;
  event_type: string;
  actor: string;
  actor_type?: string | null;
  timestamp: string;
  summary: string;
  request_id: string;
  correlation_id: string;
  policy_decision?: string | null;
  details: Record<string, unknown>;
}

export interface ExplanationBlock {
  title: string;
  body: string;
  source: "gemini" | "fallback";
  cached: boolean;
  generated_at: string;
  prompt_version: string;
}

export interface CaseDrawerModel {
  case: RecoveryCaseDetail;
  diagnosis: {
    primary: string;
    confidence: number;
    evidence: EvidenceItem[];
    triggered_rules: string[];
    version: string;
    model: string;
    contributors: ConfidenceContributor[];
  };
  policy: {
    decision: string;
    decision_priority: number;
    reasons: string[];
    allowed_channels: string[];
    blocked_channels: string[];
    cooldown_until: string | null;
    evaluated_rules: EvaluatedRuleRow[];
  };
  planner: {
    primary_strategy: string;
    fallback_strategy: string;
    scheduled_time: string | null;
    recovery_probability: number;
    expected_recovered_value: number;
    estimated_communication_cost: number;
  };
  execution: {
    status: string;
    type: string;
    idempotency_key: string | null;
    execution_id: string | null;
    scheduled_time: string | null;
    executed_time: string | null;
    webhook_replay: boolean;
  };
  explanations: {
    merchant: ExplanationBlock;
    customer: ExplanationBlock;
    compliance: ExplanationBlock;
  };
  timeline: TimelineEvent[];
  audit: AuditEvent[];
  source: "live" | "simulator";
}
