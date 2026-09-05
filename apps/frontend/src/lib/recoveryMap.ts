import type {
  ConfidenceContributor,
  EvidenceItem,
  ExplanationBlock,
  PlannerStrategy,
  PolicyDecision,
  QueueRow,
  RecoveryQueueFilters,
  RecoveryQueueItem,
  RecoveryStatus,
} from "@/types/recovery";

const PLAN_BY_PAISE: Record<number, string> = {
  49900: "FitLife Starter",
  99900: "FitLife Pro",
  149900: "FitLife Elite",
  249900: "FitLife Premium",
};

const STRATEGY_BY_REASON: Record<string, PlannerStrategy> = {
  INSUFFICIENT_FUNDS: "WAIT_FOR_PAYDAY",
  UPI_FAILURE: "RETRY_SILENTLY",
  BANK_TIMEOUT: "RETRY_SILENTLY",
  CARD_EXPIRED: "SWITCH_PAYMENT_METHOD",
  MANDATE_REVOKED: "REQUEST_NEW_MANDATE",
  CUSTOMER_CANCELLED: "STOP_RECOVERY",
  ALREADY_PAID: "STOP_RECOVERY",
  DISPUTE: "ESCALATE_TO_HUMAN",
  UNKNOWN: "RETRY_PAYMENT",
};

const FALLBACK_BY_STRATEGY: Record<string, PlannerStrategy> = {
  WAIT_FOR_PAYDAY: "SEND_PAYMENT_LINK",
  RETRY_SILENTLY: "SWITCH_PAYMENT_METHOD",
  REQUEST_NEW_MANDATE: "ESCALATE_TO_HUMAN",
  SWITCH_PAYMENT_METHOD: "SEND_PAYMENT_LINK",
  SEND_PAYMENT_LINK: "ESCALATE_TO_HUMAN",
  RETRY_PAYMENT: "SEND_PAYMENT_LINK",
  HONOUR_PROMISE_TO_PAY: "SEND_PAYMENT_LINK",
  ESCALATE_TO_HUMAN: "STOP_RECOVERY",
  STOP_RECOVERY: "STOP_RECOVERY",
};

const CHANNELS_BY_STRATEGY: Record<string, string[]> = {
  WAIT_FOR_PAYDAY: ["SMS", "WhatsApp", "UPI_PAYMENT_LINK", "Email"],
  RETRY_PAYMENT: ["SMS", "UPI_PAYMENT_LINK", "WhatsApp", "Email"],
  RETRY_SILENTLY: ["DASHBOARD_NOTIFICATION"],
  SEND_PAYMENT_LINK: ["WhatsApp", "UPI_PAYMENT_LINK", "SMS", "Email"],
  SWITCH_PAYMENT_METHOD: ["WhatsApp", "CARD_UPDATE_LINK", "SMS", "Email"],
  REQUEST_NEW_MANDATE: ["WhatsApp", "CARD_UPDATE_LINK", "Email", "SMS"],
  HONOUR_PROMISE_TO_PAY: ["WhatsApp", "SMS", "Email"],
  ESCALATE_TO_HUMAN: ["Email", "DASHBOARD_NOTIFICATION"],
  STOP_RECOVERY: [],
};

const ALL_CHANNELS = ["WhatsApp", "SMS", "Voice", "Email"] as const;

const TRIGGERED_RULES: Record<string, string[]> = {
  INSUFFICIENT_FUNDS: ["recorded_insufficient_funds", "salary_cycle_nsf", "pre_payday_window"],
  CARD_EXPIRED: ["card_expired_instrument"],
  UPI_FAILURE: ["upi_timeout_or_failure", "rail_outage_window"],
  BANK_TIMEOUT: ["bank_timeout_or_outage"],
  MANDATE_REVOKED: ["mandate_revoked_or_paused"],
  CUSTOMER_CANCELLED: ["customer_cancelled_subscription"],
  ALREADY_PAID: ["already_paid_after_failure"],
  DISPUTE: ["dispute_or_chargeback"],
  UNKNOWN: ["no_rule_fired"],
};

const EVIDENCE_BY_REASON: Record<string, EvidenceItem[]> = {
  INSUFFICIENT_FUNDS: [
    { label: "Recorded NSF", weight: 0.28, message: "Gateway recorded INSUFFICIENT_FUNDS on this invoice." },
    { label: "Salary cycle", weight: 0.1, message: "Customer is salary-dependent; payday wait is preferred." },
    { label: "Pre-payday window", weight: 0.12, message: "Failure landed in the late-month squeeze." },
  ],
  CARD_EXPIRED: [
    { label: "Instrument expired", weight: 0.32, message: "Stored card is past expiry; a method switch is required." },
    { label: "Mandate state", weight: 0.1, message: "Autopay cannot debit an expired instrument." },
  ],
  UPI_FAILURE: [
    { label: "Rail timeout", weight: 0.22, message: "UPI timed out or returned a transient failure." },
    { label: "Retry history", weight: 0.08, message: "Prior silent retries recovered similar outages." },
  ],
  BANK_TIMEOUT: [
    { label: "Issuer downtime", weight: 0.22, message: "Issuing bank timed out during capture." },
    { label: "Outage match", weight: 0.18, message: "Failure aligns with a known bank-downtime window." },
  ],
  MANDATE_REVOKED: [
    { label: "Mandate revoked", weight: 0.34, message: "Customer or bank cancelled the Autopay mandate." },
    { label: "History", weight: 0.08, message: "No successful debit after the mandate change." },
  ],
  CUSTOMER_CANCELLED: [
    { label: "Cancellation signal", weight: 0.4, message: "Subscription is cancelled; recovery must stop." },
  ],
  ALREADY_PAID: [
    { label: "Duplicate capture", weight: 0.42, message: "A successful payment already covers this invoice." },
  ],
  DISPUTE: [
    { label: "Chargeback active", weight: 0.4, message: "A dispute is open; humans must review." },
  ],
  UNKNOWN: [
    { label: "No rule fired", weight: 0.12, message: "No diagnosis rule matched; planner retries conservatively." },
    { label: "Base prior", weight: 0.2, message: "Engine started from the 0.20 confidence prior." },
  ],
};

const CONTRIBUTORS_BY_REASON: Record<string, ConfidenceContributor[]> = {
  INSUFFICIENT_FUNDS: [
    { label: "Recorded failure reason", weight: 0.28 },
    { label: "Salary / payday cycle", weight: 0.1 },
    { label: "Customer history", weight: 0.12 },
  ],
  CARD_EXPIRED: [
    { label: "Recorded failure reason", weight: 0.28 },
    { label: "Mandate state", weight: 0.1 },
  ],
  UPI_FAILURE: [
    { label: "Outage match", weight: 0.22 },
    { label: "Retry count", weight: 0.08 },
  ],
  BANK_TIMEOUT: [
    { label: "Outage match", weight: 0.22 },
    { label: "Recorded failure reason", weight: 0.28 },
  ],
  MANDATE_REVOKED: [
    { label: "Mandate state", weight: 0.1 },
    { label: "Recorded failure reason", weight: 0.28 },
  ],
  CUSTOMER_CANCELLED: [{ label: "Recorded failure reason", weight: 0.4 }],
  ALREADY_PAID: [{ label: "Duplicate capture", weight: 0.42 }],
  DISPUTE: [{ label: "Chargeback signal", weight: 0.4 }],
  UNKNOWN: [
    { label: "Base prior", weight: 0.2 },
    { label: "No matching rule", weight: 0.0 },
  ],
};

const SEGMENT_PROBABILITY: Record<string, number> = {
  HIGH_VALUE: 0.72,
  LOYAL: 0.68,
  ACTIVE: 0.58,
  AT_RISK: 0.44,
  NEW: 0.38,
  CHURN_RISK: 0.22,
};

const CHANNEL_COST_PAISE: Record<string, number> = {
  SMS: 15,
  WhatsApp: 80,
  Voice: 250,
  Email: 0,
  UPI_PAYMENT_LINK: 0,
  CARD_UPDATE_LINK: 0,
  DASHBOARD_NOTIFICATION: 0,
};

const DECISION_PRIORITY: Record<string, number> = {
  ALLOW: 20,
  WAIT: 40,
  DENY: 60,
  ESCALATE: 80,
  STOP: 100,
};

const POLICY_RULES: Record<string, { name: string; result: string; reason: string }[]> = {
  ALLOW: [
    { name: "consent", result: "PASS", reason: "Customer granted SMS / WhatsApp / Email." },
    { name: "retry_cooldown", result: "PASS", reason: "Retry gap of 24h is clear." },
    { name: "mandate", result: "PASS", reason: "Mandate is active or not required for this rail." },
    { name: "chargeback", result: "PASS", reason: "No dispute on this invoice." },
  ],
  ESCALATE: [
    { name: "high_value", result: "ESCALATE", reason: "HIGH_VALUE invoice at or above ₹1,499." },
    { name: "consent", result: "PASS", reason: "Outreach is still allowed while a human reviews." },
  ],
  STOP: [
    { name: "already_paid", result: "STOP", reason: "Invoice is already settled or recovery is forbidden." },
    { name: "mandate", result: "STOP", reason: "Mandate revoked or customer cancelled." },
  ],
  DENY: [
    { name: "churn_protection", result: "DENY", reason: "Further contact would harm a closed relationship." },
  ],
};

export const EMPTY_FILTERS: RecoveryQueueFilters = {
  search: "",
  diagnosis: "",
  policy: "",
  strategy: "",
  priority: "",
  status: "",
  amountMin: "",
  amountMax: "",
  paymentMethod: "",
  dateFrom: "",
  dateTo: "",
  segment: "",
  merchantId: "",
};

/** FitLife plan name from billing amount in paise. */
export function planNameFor(amount: number): string {
  return PLAN_BY_PAISE[amount] ?? "FitLife Membership";
}

/** Planner strategy code from the diagnosis engine mapping. */
export function plannerStrategyFor(reason: string | null | undefined, status?: string): PlannerStrategy {
  if (status === "WAITING_PROMISE") {
    return "HONOUR_PROMISE_TO_PAY";
  }
  if (status === "STOPPED" || status === "CLOSED") {
    return STRATEGY_BY_REASON[reason ?? ""] === "ESCALATE_TO_HUMAN"
      ? "ESCALATE_TO_HUMAN"
      : "STOP_RECOVERY";
  }
  if (status === "ESCALATED") {
    return "ESCALATE_TO_HUMAN";
  }
  return STRATEGY_BY_REASON[reason ?? ""] ?? "RETRY_PAYMENT";
}

/** Fallback planner strategy for the primary code. */
export function fallbackStrategyFor(primary: string): PlannerStrategy {
  return FALLBACK_BY_STRATEGY[primary] ?? "STOP_RECOVERY";
}

/** Policy fold from recovery status. Display-only; engines are not called. */
export function policyStatusFor(status: string): PolicyDecision {
  if (status === "STOPPED") {
    return "STOP";
  }
  if (status === "CLOSED") {
    return "DENY";
  }
  if (status === "ESCALATED") {
    return "ESCALATE";
  }
  return "ALLOW";
}

/** HIGH ≥ 0.8, MEDIUM 0.6–0.8, LOW < 0.6 — same bands as GET /recovery/queue. */
export function priorityBand(score: number | null | undefined): "HIGH" | "MEDIUM" | "LOW" {
  const value = score ?? 0;
  if (value >= 0.8) {
    return "HIGH";
  }
  if (value >= 0.6) {
    return "MEDIUM";
  }
  return "LOW";
}

/** Queue action chip from recovery status + planner strategy. Live chips overlay this. */
export function actionChipFor(status: string, strategy: string): string {
  if (status === "RECOVERED") {
    return "Delivered";
  }
  if (status === "STOPPED" || status === "CLOSED" || status === "ESCALATED") {
    return "Failed";
  }
  if (status === "WAITING_PROMISE") {
    return "Scheduled";
  }
  if (status === "WAITING_RETRY") {
    if (strategy === "SEND_PAYMENT_LINK" || strategy === "SWITCH_PAYMENT_METHOD" || strategy === "REQUEST_NEW_MANDATE") {
      return "Link Sent";
    }
    if (strategy === "RETRY_PAYMENT" || strategy === "RETRY_SILENTLY") {
      return "Retrying";
    }
    return "Scheduled";
  }
  return "Scheduled";
}

/** Enrich a queue DTO with display columns the API does not return. */
export function toQueueRow(item: RecoveryQueueItem): QueueRow {
  const reason = item.diagnosed_reason ?? item.failure_reason ?? "UNKNOWN";
  const planner_strategy = plannerStrategyFor(reason, item.recovery_status);
  return {
    ...item,
    plan_name: planNameFor(item.amount),
    planner_strategy,
    policy_status: policyStatusFor(item.recovery_status),
    last_updated: item.recovery_started_at ?? item.failed_at,
    action_chip: actionChipFor(item.recovery_status, planner_strategy),
  };
}

/** Diagnosis evidence catalog keyed by diagnosed_reason. */
export function evidenceFor(reason: string | null | undefined): EvidenceItem[] {
  return EVIDENCE_BY_REASON[reason ?? "UNKNOWN"] ?? EVIDENCE_BY_REASON.UNKNOWN;
}

/** Confidence-bar tooltip contributors. */
export function contributorsFor(reason: string | null | undefined): ConfidenceContributor[] {
  return CONTRIBUTORS_BY_REASON[reason ?? "UNKNOWN"] ?? CONTRIBUTORS_BY_REASON.UNKNOWN;
}

/** Diagnosis rule ids that would have fired for this reason. */
export function triggeredRulesFor(reason: string | null | undefined): string[] {
  return TRIGGERED_RULES[reason ?? "UNKNOWN"] ?? TRIGGERED_RULES.UNKNOWN;
}

/** Policy decision priority rank (higher = more blocking). */
export function decisionPriority(decision: string): number {
  return DECISION_PRIORITY[decision] ?? 20;
}

/** Channels the planner would prefer for this strategy. */
export function allowedChannelsFor(strategy: string, decision: string): string[] {
  if (decision === "STOP" || decision === "DENY") {
    return [];
  }
  return CHANNELS_BY_STRATEGY[strategy] ?? ["Email"];
}

/** Policy channels not in the allowed set. */
export function blockedChannelsFor(allowed: string[]): string[] {
  return ALL_CHANNELS.filter((channel) => !allowed.includes(channel));
}

/** Evaluated-rules table for the policy card. */
export function evaluatedRulesFor(decision: string): { policy_name: string; result: string; reason: string }[] {
  const rows = POLICY_RULES[decision] ?? POLICY_RULES.ALLOW;
  return rows.map((row) => ({
    policy_name: row.name,
    result: row.result,
    reason: row.reason,
  }));
}

/** Expected recovery probability from segment + diagnosis, clamped 0–1. */
export function recoveryProbability(segment: string, reason: string | null | undefined, status: string): number {
  if (status === "RECOVERED") {
    return 1;
  }
  if (status === "STOPPED" || status === "CLOSED") {
    return 0;
  }
  const base = SEGMENT_PROBABILITY[segment] ?? 0.5;
  const penalty = reason === "UNKNOWN" ? 0.12 : reason === "DISPUTE" ? 0.3 : 0;
  return Math.max(0.05, Math.min(0.95, base - penalty));
}

/** Estimated communication cost in paise for allowed channels. */
export function communicationCostPaise(channels: string[]): number {
  return channels.reduce((sum, channel) => sum + (CHANNEL_COST_PAISE[channel] ?? 0), 0);
}

/** Next payday-morning ISO string after a failure, used as cooldown / schedule. */
export function nextPaydayIso(fromIso: string): string {
  const stamp = new Date(fromIso);
  if (Number.isNaN(stamp.getTime())) {
    return fromIso;
  }
  const next = new Date(stamp);
  next.setDate(stamp.getDate() + 1);
  while (next.getDate() > 5) {
    next.setDate(next.getDate() + 1);
    if (next.getDate() === 1) {
      break;
    }
  }
  next.setHours(9, 15, 0, 0);
  return next.toISOString();
}

/** Fallback Gemini-shaped copy. No HTTP call; engines are never invoked. */
export function buildExplanations(input: {
  name: string;
  plan: string;
  amountLabel: string;
  diagnosis: string;
  decision: string;
  strategy: string;
  status: RecoveryStatus | string;
  generatedAt: string;
  cached: boolean;
}): { merchant: ExplanationBlock; customer: ExplanationBlock; compliance: ExplanationBlock } {
  const first = input.name.split(" ")[0] ?? input.name;
  const meta = {
    source: "fallback" as const,
    cached: input.cached,
    generated_at: input.generatedAt,
    prompt_version: "explanation_prompt_v1",
  };
  return {
    merchant: {
      title: "Merchant explanation",
      body: `${input.name}'s ${input.plan} invoice of ${input.amountLabel} failed with ${input.diagnosis.replaceAll("_", " ").toLowerCase()}. Policy folded to ${input.decision}. The planner selected ${input.strategy.replaceAll("_", " ").toLowerCase()}. Status is ${input.status.replaceAll("_", " ").toLowerCase()}.`,
      ...meta,
    },
    customer: {
      title: "Customer explanation",
      body: `Hi ${first}, we could not collect ${input.amountLabel} for your ${input.plan} membership. ${customerNextStep(input.strategy, input.status)}`,
      ...meta,
    },
    compliance: {
      title: "Compliance explanation",
      body: `Diagnosis ${input.diagnosis} was scored by recovery_diagnosis_v1. Policy ${input.decision} comes from recovery_policy_v1. Planner ${input.strategy} is recovery_planner_v1. Gemini is not called over HTTP in this phase; this copy is the fallback template.`,
      ...meta,
    },
  };
}

function customerNextStep(strategy: string, status: string): string {
  if (status === "RECOVERED") {
    return "This invoice is already captured. No further action is needed.";
  }
  if (strategy === "WAIT_FOR_PAYDAY" || strategy === "HONOUR_PROMISE_TO_PAY") {
    return "We will retry automatically after salary credit. You do not need to do anything now.";
  }
  if (strategy === "RETRY_SILENTLY") {
    return "A silent retry is scheduled once the payment rail recovers.";
  }
  if (strategy === "SWITCH_PAYMENT_METHOD") {
    return "Please update your card when you have a moment. No extra charge will apply.";
  }
  if (strategy === "STOP_RECOVERY") {
    return "We have stopped further collection attempts on this invoice.";
  }
  if (strategy === "ESCALATE_TO_HUMAN") {
    return "A FitLife billing specialist will review this payment shortly.";
  }
  return "We will send a secure payment link if the next attempt needs your confirmation.";
}

function parseRupees(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }
  const value = Number(trimmed);
  if (!Number.isFinite(value)) {
    return null;
  }
  return Math.round(value * 100);
}

/** Client-side filters the queue API does not accept. */
export function applyClientFilters(rows: QueueRow[], filters: RecoveryQueueFilters): QueueRow[] {
  const needle = filters.search.trim().toLowerCase();
  const minPaise = parseRupees(filters.amountMin);
  const maxPaise = parseRupees(filters.amountMax);
  return rows.filter((row) => {
    if (needle) {
      const hay = `${row.customer_name} ${row.payment_id} ${row.recovery_case_id}`.toLowerCase();
      if (!hay.includes(needle)) {
        return false;
      }
    }
    if (filters.diagnosis && (row.diagnosed_reason ?? row.failure_reason) !== filters.diagnosis) {
      return false;
    }
    if (filters.policy && row.policy_status !== filters.policy) {
      return false;
    }
    if (filters.strategy && row.planner_strategy !== filters.strategy) {
      return false;
    }
    if (filters.priority && priorityBand(row.priority_score) !== filters.priority) {
      return false;
    }
    if (filters.status && row.recovery_status !== filters.status) {
      return false;
    }
    if (filters.paymentMethod && row.payment_method !== filters.paymentMethod) {
      return false;
    }
    if (filters.segment && row.customer_segment !== filters.segment) {
      return false;
    }
    if (minPaise != null && row.amount < minPaise) {
      return false;
    }
    if (maxPaise != null && row.amount > maxPaise) {
      return false;
    }
    if (filters.dateFrom && row.failed_at.slice(0, 10) < filters.dateFrom) {
      return false;
    }
    if (filters.dateTo && row.failed_at.slice(0, 10) > filters.dateTo) {
      return false;
    }
    return true;
  });
}

const ADVANCED_FILTER_KEYS: (keyof RecoveryQueueFilters)[] = [
  "policy",
  "strategy",
  "paymentMethod",
  "segment",
  "amountMin",
  "amountMax",
  "dateFrom",
  "dateTo",
];

/** True when any filter besides merchant is set. */
export function hasActiveFilters(filters: RecoveryQueueFilters): boolean {
  return (Object.keys(EMPTY_FILTERS) as (keyof RecoveryQueueFilters)[]).some((key) => {
    if (key === "merchantId") {
      return false;
    }
    return filters[key] !== EMPTY_FILTERS[key];
  });
}

/** Count of less-used filters sitting behind Advanced Filters. */
export function advancedFilterCount(filters: RecoveryQueueFilters): number {
  return ADVANCED_FILTER_KEYS.filter((key) => filters[key] !== EMPTY_FILTERS[key]).length;
}
