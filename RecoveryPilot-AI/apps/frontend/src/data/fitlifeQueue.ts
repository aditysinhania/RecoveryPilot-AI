import snapshotJson from "@/data/fitlifeSnapshot.json";
import { formatPaise } from "@/lib/format";
import {
  allowedChannelsFor,
  blockedChannelsFor,
  buildExplanations,
  communicationCostPaise,
  contributorsFor,
  decisionPriority,
  evaluatedRulesFor,
  evidenceFor,
  fallbackStrategyFor,
  nextPaydayIso,
  plannerStrategyFor,
  planNameFor,
  policyStatusFor,
  recoveryProbability,
  toQueueRow,
  triggeredRulesFor,
} from "@/lib/recoveryMap";
import type { FitlifeSnapshot } from "@/types/dashboard";
import type {
  AuditEvent,
  CaseDrawerModel,
  QueueRow,
  RecoveryCaseDetail,
  RecoveryQueueItem,
  RecoveryQueueSummary,
  TimelineEvent,
} from "@/types/recovery";

const SNAPSHOT = snapshotJson as FitlifeSnapshot;

export const FITLIFE_AS_OF = SNAPSHOT.as_of;
export const FITLIFE_MERCHANT_ID = SNAPSHOT.merchant.id;
export const FITLIFE_LIST_ID = SNAPSHOT.merchant.list_id;

interface SeedRow {
  recovery_case_id: string;
  customer_name: string;
  customer_segment: string;
  amount: number;
  diagnosed_reason: string;
  recovery_status: string;
  priority_score: number;
  ai_confidence: number;
  payment_method: string;
  failed_at: string;
}

const TOP = SNAPSHOT.top_customers;

const SEED: SeedRow[] = [
  {
    recovery_case_id: TOP[0].recovery_case_id,
    customer_name: TOP[0].customer_name,
    customer_segment: TOP[0].customer_segment,
    amount: TOP[0].amount,
    diagnosed_reason: TOP[0].diagnosis,
    recovery_status: TOP[0].recovery_status,
    priority_score: TOP[0].priority_score,
    ai_confidence: 0.86,
    payment_method: "UPI",
    failed_at: TOP[0].failed_at ?? "2026-09-02T07:12:00+05:30",
  },
  {
    recovery_case_id: TOP[1].recovery_case_id,
    customer_name: TOP[1].customer_name,
    customer_segment: TOP[1].customer_segment,
    amount: TOP[1].amount,
    diagnosed_reason: TOP[1].diagnosis,
    recovery_status: TOP[1].recovery_status,
    priority_score: TOP[1].priority_score,
    ai_confidence: 0.84,
    payment_method: "UPI",
    failed_at: TOP[1].failed_at ?? "2026-08-26T07:12:00+05:30",
  },
  {
    recovery_case_id: TOP[2].recovery_case_id,
    customer_name: TOP[2].customer_name,
    customer_segment: TOP[2].customer_segment,
    amount: TOP[2].amount,
    diagnosed_reason: TOP[2].diagnosis,
    recovery_status: TOP[2].recovery_status,
    priority_score: TOP[2].priority_score,
    ai_confidence: 0.41,
    payment_method: "CARD",
    failed_at: TOP[2].failed_at ?? "2026-07-24T07:12:00+05:30",
  },
  {
    recovery_case_id: TOP[3].recovery_case_id,
    customer_name: TOP[3].customer_name,
    customer_segment: TOP[3].customer_segment,
    amount: TOP[3].amount,
    diagnosed_reason: TOP[3].diagnosis,
    recovery_status: TOP[3].recovery_status,
    priority_score: TOP[3].priority_score,
    ai_confidence: 0.81,
    payment_method: "UPI",
    failed_at: TOP[3].failed_at ?? "2026-08-28T07:12:00+05:30",
  },
  {
    recovery_case_id: TOP[4].recovery_case_id,
    customer_name: TOP[4].customer_name,
    customer_segment: TOP[4].customer_segment,
    amount: TOP[4].amount,
    diagnosed_reason: TOP[4].diagnosis,
    recovery_status: TOP[4].recovery_status,
    priority_score: TOP[4].priority_score,
    ai_confidence: 0.39,
    payment_method: "NETBANKING",
    failed_at: TOP[4].failed_at ?? "2026-06-23T07:12:00+05:30",
  },
  {
    recovery_case_id: TOP[5].recovery_case_id,
    customer_name: TOP[5].customer_name,
    customer_segment: TOP[5].customer_segment,
    amount: TOP[5].amount,
    diagnosed_reason: TOP[5].diagnosis,
    recovery_status: TOP[5].recovery_status,
    priority_score: TOP[5].priority_score,
    ai_confidence: 0.44,
    payment_method: "UPI",
    failed_at: TOP[5].failed_at ?? "2026-08-23T07:12:00+05:30",
  },
  {
    recovery_case_id: TOP[6].recovery_case_id,
    customer_name: TOP[6].customer_name,
    customer_segment: TOP[6].customer_segment,
    amount: TOP[6].amount,
    diagnosed_reason: TOP[6].diagnosis,
    recovery_status: TOP[6].recovery_status,
    priority_score: TOP[6].priority_score,
    ai_confidence: 0.79,
    payment_method: "MANDATE",
    failed_at: TOP[6].failed_at ?? "2026-09-01T07:12:00+05:30",
  },
  {
    recovery_case_id: TOP[7].recovery_case_id,
    customer_name: TOP[7].customer_name,
    customer_segment: TOP[7].customer_segment,
    amount: TOP[7].amount,
    diagnosed_reason: TOP[7].diagnosis,
    recovery_status: TOP[7].recovery_status,
    priority_score: TOP[7].priority_score,
    ai_confidence: 0.8,
    payment_method: "UPI",
    failed_at: TOP[7].failed_at ?? "2026-08-28T07:12:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000009",
    customer_name: "Rohan Iyer",
    customer_segment: "ACTIVE",
    amount: 49900,
    diagnosed_reason: "UPI_FAILURE",
    recovery_status: "WAITING_RETRY",
    priority_score: 0.64,
    ai_confidence: 0.71,
    payment_method: "UPI",
    failed_at: "2026-09-01T18:40:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000010",
    customer_name: "Diya Nair",
    customer_segment: "LOYAL",
    amount: 99900,
    diagnosed_reason: "BANK_TIMEOUT",
    recovery_status: "WAITING_RETRY",
    priority_score: 0.7,
    ai_confidence: 0.74,
    payment_method: "NETBANKING",
    failed_at: "2026-08-31T11:05:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000011",
    customer_name: "Kabir Khan",
    customer_segment: "HIGH_VALUE",
    amount: 249900,
    diagnosed_reason: "CARD_EXPIRED",
    recovery_status: "WAITING_RETRY",
    priority_score: 0.91,
    ai_confidence: 0.88,
    payment_method: "CARD",
    failed_at: "2026-08-30T09:22:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000012",
    customer_name: "Sneha Rao",
    customer_segment: "AT_RISK",
    amount: 99900,
    diagnosed_reason: "INSUFFICIENT_FUNDS",
    recovery_status: "WAITING_PROMISE",
    priority_score: 0.73,
    ai_confidence: 0.77,
    payment_method: "UPI",
    failed_at: "2026-08-29T21:10:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000013",
    customer_name: "Vikram Patel",
    customer_segment: "LOYAL",
    amount: 149900,
    diagnosed_reason: "DISPUTE",
    recovery_status: "ESCALATED",
    priority_score: 0.94,
    ai_confidence: 0.9,
    payment_method: "CARD",
    failed_at: "2026-08-27T14:18:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000014",
    customer_name: "Ishita Shah",
    customer_segment: "CHURN_RISK",
    amount: 49900,
    diagnosed_reason: "CUSTOMER_CANCELLED",
    recovery_status: "STOPPED",
    priority_score: 0.22,
    ai_confidence: 0.91,
    payment_method: "UPI",
    failed_at: "2026-08-20T08:00:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000015",
    customer_name: "Nikhil Verma",
    customer_segment: "NEW",
    amount: 49900,
    diagnosed_reason: "ALREADY_PAID",
    recovery_status: "STOPPED",
    priority_score: 0.18,
    ai_confidence: 0.93,
    payment_method: "UPI",
    failed_at: "2026-09-02T08:30:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000016",
    customer_name: "Pooja Desai",
    customer_segment: "ACTIVE",
    amount: 99900,
    diagnosed_reason: "MANDATE_REVOKED",
    recovery_status: "STOPPED",
    priority_score: 0.35,
    ai_confidence: 0.87,
    payment_method: "MANDATE",
    failed_at: "2026-08-18T16:45:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000017",
    customer_name: "Aditya Nair",
    customer_segment: "LOYAL",
    amount: 99900,
    diagnosed_reason: "INSUFFICIENT_FUNDS",
    recovery_status: "RECOVERED",
    priority_score: 0.81,
    ai_confidence: 0.83,
    payment_method: "UPI",
    failed_at: "2026-08-25T07:12:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000018",
    customer_name: "Tanvi Kulkarni",
    customer_segment: "HIGH_VALUE",
    amount: 149900,
    diagnosed_reason: "UPI_FAILURE",
    recovery_status: "RECOVERED",
    priority_score: 0.88,
    ai_confidence: 0.76,
    payment_method: "UPI",
    failed_at: "2026-09-01T19:20:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000019",
    customer_name: "Farhan Ali",
    customer_segment: "ACTIVE",
    amount: 49900,
    diagnosed_reason: "BANK_TIMEOUT",
    recovery_status: "RECOVERED",
    priority_score: 0.61,
    ai_confidence: 0.7,
    payment_method: "NETBANKING",
    failed_at: "2026-09-02T06:05:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000020",
    customer_name: "Rhea Kapoor",
    customer_segment: "LOYAL",
    amount: 99900,
    diagnosed_reason: "CARD_EXPIRED",
    recovery_status: "RECOVERED",
    priority_score: 0.77,
    ai_confidence: 0.85,
    payment_method: "CARD",
    failed_at: "2026-08-22T10:00:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000021",
    customer_name: "Mohit Agarwal",
    customer_segment: "AT_RISK",
    amount: 99900,
    diagnosed_reason: "UNKNOWN",
    recovery_status: "ESCALATED",
    priority_score: 0.66,
    ai_confidence: 0.36,
    payment_method: "WALLET",
    failed_at: "2026-08-21T13:40:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000022",
    customer_name: "Sana Qureshi",
    customer_segment: "NEW",
    amount: 49900,
    diagnosed_reason: "UPI_FAILURE",
    recovery_status: "DIAGNOSED",
    priority_score: 0.52,
    ai_confidence: 0.68,
    payment_method: "UPI",
    failed_at: "2026-09-02T12:10:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000023",
    customer_name: "Dev Sharma",
    customer_segment: "ACTIVE",
    amount: 99900,
    diagnosed_reason: "INSUFFICIENT_FUNDS",
    recovery_status: "OPEN",
    priority_score: 0.58,
    ai_confidence: 0.62,
    payment_method: "UPI",
    failed_at: "2026-09-02T16:40:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000024",
    customer_name: "Nisha Pillai",
    customer_segment: "LOYAL",
    amount: 149900,
    diagnosed_reason: "BANK_TIMEOUT",
    recovery_status: "WAITING_RETRY",
    priority_score: 0.76,
    ai_confidence: 0.73,
    payment_method: "NETBANKING",
    failed_at: "2026-08-28T22:15:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000025",
    customer_name: "Leela Krishnan",
    customer_segment: "HIGH_VALUE",
    amount: 249900,
    diagnosed_reason: "INSUFFICIENT_FUNDS",
    recovery_status: "WAITING_PROMISE",
    priority_score: 0.97,
    ai_confidence: 0.89,
    payment_method: "MANDATE",
    failed_at: "2026-08-31T07:12:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000026",
    customer_name: "Amit Bose",
    customer_segment: "CHURN_RISK",
    amount: 49900,
    diagnosed_reason: "CUSTOMER_CANCELLED",
    recovery_status: "STOPPED",
    priority_score: 0.2,
    ai_confidence: 0.9,
    payment_method: "UPI",
    failed_at: "2026-08-12T09:00:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000027",
    customer_name: "Priya Iyer",
    customer_segment: "LOYAL",
    amount: 99900,
    diagnosed_reason: "DISPUTE",
    recovery_status: "ESCALATED",
    priority_score: 0.85,
    ai_confidence: 0.88,
    payment_method: "CARD",
    failed_at: "2026-08-19T17:30:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000028",
    customer_name: "Sahil Gupta",
    customer_segment: "ACTIVE",
    amount: 49900,
    diagnosed_reason: "UPI_FAILURE",
    recovery_status: "WAITING_RETRY",
    priority_score: 0.55,
    ai_confidence: 0.69,
    payment_method: "UPI",
    failed_at: "2026-09-02T04:50:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000029",
    customer_name: "Anika Reddy",
    customer_segment: "LOYAL",
    amount: 149900,
    diagnosed_reason: "CARD_EXPIRED",
    recovery_status: "WAITING_RETRY",
    priority_score: 0.82,
    ai_confidence: 0.84,
    payment_method: "CARD",
    failed_at: "2026-08-26T11:11:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000030",
    customer_name: "Harsh Malhotra",
    customer_segment: "NEW",
    amount: 49900,
    diagnosed_reason: "UNKNOWN",
    recovery_status: "DIAGNOSED",
    priority_score: 0.48,
    ai_confidence: 0.33,
    payment_method: "WALLET",
    failed_at: "2026-09-02T15:05:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000031",
    customer_name: "Tara Banerjee",
    customer_segment: "HIGH_VALUE",
    amount: 249900,
    diagnosed_reason: "INSUFFICIENT_FUNDS",
    recovery_status: "RECOVERED",
    priority_score: 0.93,
    ai_confidence: 0.87,
    payment_method: "UPI",
    failed_at: "2026-08-28T07:12:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000032",
    customer_name: "Yash Jain",
    customer_segment: "ACTIVE",
    amount: 99900,
    diagnosed_reason: "BANK_TIMEOUT",
    recovery_status: "WAITING_RETRY",
    priority_score: 0.63,
    ai_confidence: 0.72,
    payment_method: "NETBANKING",
    failed_at: "2026-08-30T20:00:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000033",
    customer_name: "Megha Rao",
    customer_segment: "LOYAL",
    amount: 99900,
    diagnosed_reason: "MANDATE_REVOKED",
    recovery_status: "STOPPED",
    priority_score: 0.4,
    ai_confidence: 0.86,
    payment_method: "MANDATE",
    failed_at: "2026-08-15T12:00:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000034",
    customer_name: "Omar Sheikh",
    customer_segment: "AT_RISK",
    amount: 49900,
    diagnosed_reason: "INSUFFICIENT_FUNDS",
    recovery_status: "WAITING_PROMISE",
    priority_score: 0.69,
    ai_confidence: 0.75,
    payment_method: "UPI",
    failed_at: "2026-08-27T07:12:00+05:30",
  },
  {
    recovery_case_id: "a0100000-0000-4000-8000-000000000035",
    customer_name: "Kiara Das",
    customer_segment: "LOYAL",
    amount: 149900,
    diagnosed_reason: "UPI_FAILURE",
    recovery_status: "ESCALATED",
    priority_score: 0.8,
    ai_confidence: 0.64,
    payment_method: "UPI",
    failed_at: "2026-08-24T18:18:00+05:30",
  },
  {
    recovery_case_id: "9799ee6a-eb74-5153-814b-0509db6787ac",
    customer_name: "Arjun Reddy",
    customer_segment: "LOYAL",
    amount: 149900,
    diagnosed_reason: "INSUFFICIENT_FUNDS",
    recovery_status: "RECOVERED",
    priority_score: 0.8,
    ai_confidence: 0.82,
    payment_method: "UPI",
    failed_at: "2026-08-20T07:12:00+05:30",
  },
];

function slug(name: string, index: number): string {
  return name.toLowerCase().replace(/[^a-z]+/g, ".") + index;
}

function seedToItem(seed: SeedRow, index: number): RecoveryQueueItem {
  const started =
    seed.recovery_status === "OPEN"
      ? null
      : new Date(Date.parse(seed.failed_at) + 6 * 60_000).toISOString();
  return {
    recovery_case_id: seed.recovery_case_id,
    merchant_id: FITLIFE_MERCHANT_ID,
    customer_id: `c0100000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
    payment_id: `p0100000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
    customer_name: seed.customer_name,
    customer_segment: seed.customer_segment,
    amount: seed.amount,
    currency: "INR",
    payment_method: seed.payment_method,
    failure_reason: seed.diagnosed_reason,
    diagnosed_reason: seed.diagnosed_reason,
    recovery_status: seed.recovery_status,
    priority_score: seed.priority_score,
    ai_confidence: seed.ai_confidence,
    payment_due_date: seed.failed_at.slice(0, 10),
    failed_at: seed.failed_at,
    recovery_started_at: started,
  };
}

export const SNAPSHOT_QUEUE: QueueRow[] = SEED.map((seed, index) => toQueueRow(seedToItem(seed, index)));

export const SNAPSHOT_SUMMARY: RecoveryQueueSummary = {
  open_cases: SNAPSHOT.recovery_summary.open_cases,
  recovered_cases: SNAPSHOT.recovery_summary.recovered_cases,
  stopped_cases: SNAPSHOT.recovery_summary.stopped_cases,
  escalated_cases: SNAPSHOT.recovery_summary.escalated_cases,
  waiting_retry: SNAPSHOT.recovery_summary.waiting_retry,
  waiting_promise: SNAPSHOT.recovery_summary.waiting_promise,
  total_revenue_at_risk: SNAPSHOT.recovery_summary.total_revenue_at_risk,
  recovered_revenue: SNAPSHOT.recovery_summary.recovered_revenue,
  recovery_rate: SNAPSHOT.recovery_summary.recovery_rate,
  recovered_today: SNAPSHOT_QUEUE.filter(
    (row) => row.recovery_status === "RECOVERED" && row.last_updated.slice(0, 10) === FITLIFE_AS_OF.slice(0, 10),
  ).length,
};

function addMinutes(iso: string, minutes: number): string {
  return new Date(Date.parse(iso) + minutes * 60_000).toISOString();
}

function actionTypeFor(strategy: string): string {
  if (strategy === "WAIT_FOR_PAYDAY" || strategy === "HONOUR_PROMISE_TO_PAY") {
    return "WAIT";
  }
  if (strategy === "RETRY_SILENTLY" || strategy === "RETRY_PAYMENT") {
    return "RETRY_PAYMENT";
  }
  if (strategy === "SEND_PAYMENT_LINK") {
    return "GENERATE_PAYMENT_LINK";
  }
  if (strategy === "SWITCH_PAYMENT_METHOD") {
    return "SWITCH_PAYMENT_METHOD";
  }
  if (strategy === "ESCALATE_TO_HUMAN") {
    return "ESCALATE";
  }
  if (strategy === "STOP_RECOVERY") {
    return "NO_ACTION";
  }
  return "RETRY_PAYMENT";
}

function executionStatusFor(status: string): string {
  if (status === "RECOVERED") {
    return "EXECUTED";
  }
  if (status === "STOPPED" || status === "CLOSED") {
    return "SKIPPED";
  }
  if (status === "ESCALATED") {
    return "FAILED";
  }
  if (status === "WAITING_PROMISE" || status === "WAITING_RETRY" || status === "DIAGNOSED") {
    return "SCHEDULED";
  }
  return "PENDING";
}

/** Build a read-only drawer model from a FitLife snapshot queue row. */
export function buildSnapshotCase(row: QueueRow): CaseDrawerModel {
  const reason = row.diagnosed_reason ?? row.failure_reason ?? "UNKNOWN";
  const strategy = plannerStrategyFor(reason, row.recovery_status);
  const fallback = fallbackStrategyFor(strategy);
  const decision = policyStatusFor(row.recovery_status);
  const allowed = allowedChannelsFor(strategy, decision);
  const blocked = blockedChannelsFor(allowed);
  const scheduled = row.recovery_status === "WAITING_PROMISE" || strategy === "WAIT_FOR_PAYDAY"
    ? nextPaydayIso(row.failed_at)
    : addMinutes(row.failed_at, 60);
  const executed =
    row.recovery_status === "RECOVERED" || row.recovery_status === "STOPPED"
      ? addMinutes(row.failed_at, 90)
      : null;
  const plan = planNameFor(row.amount);
  const probability = recoveryProbability(row.customer_segment, reason, row.recovery_status);
  const nameSlug = slug(row.customer_name, 1);
  const caseDetail: RecoveryCaseDetail = {
    recovery_case_id: row.recovery_case_id,
    merchant_id: row.merchant_id,
    recovery_status: row.recovery_status,
    diagnosed_reason: reason,
    diagnosis_model: "recovery_diagnosis_v1",
    diagnosis_version: "1.0.0",
    ai_confidence: row.ai_confidence,
    priority_score: row.priority_score,
    recovery_started_at: row.recovery_started_at,
    recovery_completed_at: executed,
    created_at: row.failed_at,
    updated_at: row.last_updated,
    customer: {
      id: row.customer_id,
      merchant_id: row.merchant_id,
      full_name: row.customer_name,
      email: `${nameSlug}@fitlife.example`,
      phone: "+918045550100",
      customer_segment: row.customer_segment,
      preferred_payment_method: row.payment_method,
      preferred_language: "en",
      consent_status: "GRANTED",
      created_at: row.failed_at,
      updated_at: row.last_updated,
    },
    payment: {
      id: row.payment_id,
      merchant_id: row.merchant_id,
      customer_id: row.customer_id,
      subscription_id: `s-${row.recovery_case_id.slice(0, 8)}`,
      razorpay_order_id: `order_${row.recovery_case_id.slice(0, 8)}`,
      razorpay_payment_id: row.recovery_status === "RECOVERED" ? `pay_${row.recovery_case_id.slice(0, 8)}` : null,
      idempotency_key: `pay:${row.payment_id}:retry:1`,
      payment_status: row.recovery_status === "RECOVERED" ? "CAPTURED" : "FAILED",
      failure_reason: reason,
      payment_method: row.payment_method,
      amount: row.amount,
      currency: row.currency,
      attempt_number: 1,
      payment_due_date: row.payment_due_date,
      paid_at: row.recovery_status === "RECOVERED" ? executed : null,
      created_at: row.failed_at,
      updated_at: row.last_updated,
    },
    subscription: {
      id: `s-${row.recovery_case_id.slice(0, 8)}`,
      subscription_name: plan,
      billing_amount: row.amount,
      billing_frequency: "MONTHLY",
      next_billing_date: "2026-10-02",
      mandate_status: reason === "MANDATE_REVOKED" ? "REVOKED" : "ACTIVE",
      subscription_status: reason === "CUSTOMER_CANCELLED" ? "CANCELLED" : "ACTIVE",
    },
    latest_action: {
      id: `act-${row.recovery_case_id.slice(0, 8)}`,
      recovery_case_id: row.recovery_case_id,
      action_type: actionTypeFor(strategy),
      scheduled_time: scheduled,
      executed_time: executed,
      execution_status: executionStatusFor(row.recovery_status),
      razorpay_payment_link: strategy.includes("LINK") || strategy === "SEND_PAYMENT_LINK"
        ? `https://rzp.io/i/${row.recovery_case_id.slice(0, 8)}`
        : null,
      retry_number: 1,
      response_code: row.recovery_status === "RECOVERED" ? "captured" : null,
      response_message: null,
      action_metadata: {
        planner_strategy: strategy,
        webhook_replay: false,
      },
      created_at: addMinutes(row.failed_at, 8),
    },
    promise_to_pay:
      row.recovery_status === "WAITING_PROMISE"
        ? {
            id: `ptp-${row.recovery_case_id.slice(0, 8)}`,
            promised_amount: row.amount,
            promised_date: nextPaydayIso(row.failed_at).slice(0, 10),
            promise_status: "ACTIVE",
            fulfilled_at: null,
          }
        : null,
    promise_status: row.recovery_status === "WAITING_PROMISE" ? "ACTIVE" : null,
  };

  const timeline: TimelineEvent[] = [
    {
      event_type: "payment_failed",
      occurred_at: row.failed_at,
      summary: `Payment failed: ${reason}`,
      source: "razorpay",
      reference_id: row.payment_id,
      details: { failure_reason: reason, amount: row.amount, payment_method: row.payment_method },
    },
    {
      event_type: "diagnosis_created",
      occurred_at: addMinutes(row.failed_at, 4),
      summary: `Diagnosed ${reason} (${Math.round((row.ai_confidence ?? 0) * 100)}% confidence)`,
      source: "diagnosis_engine",
      reference_id: row.recovery_case_id,
      details: {
        diagnosed_reason: reason,
        confidence: row.ai_confidence,
        model: "recovery_diagnosis_v1",
        version: "1.0.0",
      },
    },
    {
      event_type: "audit",
      occurred_at: addMinutes(row.failed_at, 5),
      summary: `Policy ${decision}`,
      source: "policy_engine",
      reference_id: row.recovery_case_id,
      details: { decision, policy_version: "recovery_policy_v1" },
    },
    {
      event_type: "action_scheduled",
      occurred_at: addMinutes(row.failed_at, 8),
      summary: `Planned ${strategy}`,
      source: "planner_engine",
      reference_id: caseDetail.latest_action?.id ?? null,
      details: { strategy, fallback, scheduled_time: scheduled },
    },
  ];

  if (caseDetail.latest_action && caseDetail.latest_action.execution_status !== "PENDING") {
    timeline.push({
      event_type: "action_executed",
      occurred_at: executed ?? scheduled,
      summary: `Execution ${caseDetail.latest_action.execution_status}`,
      source: "executor",
      reference_id: caseDetail.latest_action.id,
      details: {
        action_type: caseDetail.latest_action.action_type,
        execution_status: caseDetail.latest_action.execution_status,
      },
    });
  }

  if (row.recovery_status === "RECOVERED") {
    timeline.push({
      event_type: "webhook_update",
      occurred_at: executed ?? scheduled,
      summary: "Webhook received: payment.captured",
      source: "razorpay_webhook",
      reference_id: row.payment_id,
      details: { event: "payment.captured", duplicate: false },
    });
  }

  const correlation = `corr-${row.recovery_case_id.slice(0, 8)}`;
  const audit: AuditEvent[] = timeline.map((event, index) => ({
    event_id: `aud-${row.recovery_case_id.slice(0, 8)}-${index}`,
    recovery_case_id: row.recovery_case_id,
    event_type: event.event_type.toUpperCase(),
    actor: event.source,
    actor_type: event.source === "razorpay" || event.source === "razorpay_webhook" ? "SYSTEM" : "ENGINE",
    timestamp: event.occurred_at,
    summary: event.summary,
    request_id: `req-${row.recovery_case_id.slice(0, 8)}-${index}`,
    correlation_id: correlation,
    policy_decision: event.event_type === "audit" ? decision : null,
    details: event.details,
  }));

  return {
    case: caseDetail,
    diagnosis: {
      primary: reason,
      confidence: row.ai_confidence ?? 0,
      evidence: evidenceFor(reason),
      triggered_rules: triggeredRulesFor(reason),
      version: "1.0.0",
      model: "recovery_diagnosis_v1",
      contributors: contributorsFor(reason),
    },
    policy: {
      decision,
      decision_priority: decisionPriority(decision),
      reasons: evaluatedRulesFor(decision)
        .filter((rule) => rule.result !== "PASS")
        .map((rule) => rule.reason),
      allowed_channels: allowed,
      blocked_channels: blocked,
      cooldown_until:
        row.recovery_status === "WAITING_RETRY" || row.recovery_status === "WAITING_PROMISE" ? scheduled : null,
      evaluated_rules: evaluatedRulesFor(decision),
    },
    planner: {
      primary_strategy: strategy,
      fallback_strategy: fallback,
      scheduled_time: scheduled,
      recovery_probability: probability,
      expected_recovered_value: Math.round(row.amount * probability),
      estimated_communication_cost: communicationCostPaise(allowed),
    },
    execution: {
      status: caseDetail.latest_action?.execution_status ?? "PENDING",
      type: caseDetail.latest_action?.action_type ?? "NONE",
      idempotency_key: caseDetail.payment.idempotency_key ?? null,
      execution_id: caseDetail.latest_action?.id ?? null,
      scheduled_time: scheduled,
      executed_time: executed,
      webhook_replay: false,
      display_status: caseDetail.latest_action?.execution_status ?? "PENDING",
      payment_link: caseDetail.latest_action?.razorpay_payment_link ?? null,
      retry_attempts: caseDetail.latest_action?.retry_number ?? 0,
      delivery_status: null,
      action_chip: row.action_chip,
      live: false,
    },
    explanations: buildExplanations({
      name: row.customer_name,
      plan,
      amountLabel: formatPaise(row.amount),
      diagnosis: reason,
      decision,
      strategy,
      status: row.recovery_status,
      generatedAt: row.last_updated,
      cached: true,
    }),
    timeline,
    audit,
    source: "simulator",
  };
}

export function snapshotCaseById(recoveryCaseId: string): CaseDrawerModel | null {
  const row = SNAPSHOT_QUEUE.find((item) => item.recovery_case_id === recoveryCaseId);
  return row ? buildSnapshotCase(row) : null;
}
