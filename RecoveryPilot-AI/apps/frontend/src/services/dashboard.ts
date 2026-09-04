import snapshotJson from "@/data/fitlifeSnapshot.json";
import { getData, getPage } from "@/lib/api";
import { formatPercent } from "@/lib/format";
import type {
  ActivityItem,
  AiLift,
  AuditEventItem,
  DashboardInsight,
  DashboardView,
  FailureReasonSlice,
  FitlifeSnapshot,
  FunnelStage,
  MerchantMetrics,
  MerchantOption,
  MerchantSummary,
  PaymentListItem,
  RecoveryQueueItem,
  RecoverySummary,
  TopCustomerRow,
  TrendPoint,
} from "@/types/dashboard";

export const FITLIFE_LIST_ID = "00000000-0000-4000-8000-000000000001";
export const SNAPSHOT = snapshotJson as FitlifeSnapshot;

const FAILURE_LABELS: Record<string, string> = {
  INSUFFICIENT_FUNDS: "NSF",
  CARD_EXPIRED: "Card Expired",
  UPI_FAILURE: "UPI Failure",
  MANDATE_REVOKED: "Mandate Revoked",
  BANK_TIMEOUT: "Bank Downtime",
  CUSTOMER_CANCELLED: "Other",
  ALREADY_PAID: "Other",
  DISPUTE: "Other",
  UNKNOWN: "Other",
};

const STRATEGY_BY_REASON: Record<string, string> = {
  INSUFFICIENT_FUNDS: "Wait for payday",
  UPI_FAILURE: "Silent retry",
  BANK_TIMEOUT: "Silent retry",
  CARD_EXPIRED: "Card update link",
  MANDATE_REVOKED: "Payment link",
  CUSTOMER_CANCELLED: "Stop recovery",
  ALREADY_PAID: "No action",
  DISPUTE: "Escalate to agent",
  UNKNOWN: "Diagnose and retry",
};

const PLAN_BY_PAISE: Record<number, string> = {
  49900: "FitLife Starter",
  99900: "FitLife Pro",
  149900: "FitLife Elite",
  249900: "FitLife Premium",
};

function clampSummary(text: string): string {
  if (text.length <= 160) {
    return text;
  }
  return `${text.slice(0, 157)}...`;
}

function environmentLabel(): string {
  const mode = import.meta.env.MODE;
  if (mode === "production") {
    return "Production";
  }
  if (mode === "staging") {
    return "Staging";
  }
  return "Development";
}

function buildLift(snapshot: FitlifeSnapshot, recovered: number, rate: number): AiLift {
  return {
    recovered_by_ai: recovered,
    recovered_by_baseline: snapshot.baseline.recovered_revenue,
    extra_revenue: recovered - snapshot.baseline.recovered_revenue,
    harmful_retries_prevented: snapshot.harmful_retries_prevented,
    communication_cost_saved: snapshot.communication_costs.saved_paise,
    ai_outreach_paise: snapshot.communication_costs.ai_total_paise,
    baseline_outreach_paise: snapshot.communication_costs.baseline_total_paise,
    ai_rate: rate,
    baseline_rate: snapshot.baseline.recovery_rate,
  };
}

function buildInsights(view: {
  failureReasons: FailureReasonSlice[];
  lift: AiLift;
  health: DashboardView["health"];
  generatedAt: string;
}): DashboardInsight[] {
  const nsf = view.failureReasons.find((item) => item.key === "INSUFFICIENT_FUNDS");
  const nsfShare = nsf
    ? nsf.count / view.failureReasons.reduce((sum, item) => sum + item.count, 0)
    : 0;
  const liftPct = view.lift.ai_rate - view.lift.baseline_rate;
  return [
    {
      title: "NSF still dominates at-risk revenue",
      summary: clampSummary(
        `Insufficient funds is ${formatPercent(nsfShare)} of failed invoices. Payday waits recover more than immediate retries.`,
      ),
      risk_level: "HIGH",
      next_action: "Keep NSF cases on payday wait — do not blast retries.",
      source: "fallback",
      cached: true,
      generated_at: view.generatedAt,
    },
    {
      title: "AI lift versus immediate-retry baseline",
      summary: clampSummary(
        `RecoveryPilot recovers ${formatPercent(view.lift.ai_rate)} versus ${formatPercent(view.lift.baseline_rate)} baseline (${formatPercent(liftPct)} lift).`,
      ),
      risk_level: "MEDIUM",
      next_action: "Protect stopping rules on revoked mandates and disputes.",
      source: "fallback",
      cached: true,
      generated_at: view.generatedAt,
    },
    {
      title: view.health.promise_active
        ? "Promise-to-pay cases still open"
        : "Waiting queue is quiet",
      summary: clampSummary(
        `${view.health.cases_waiting} cases are waiting and ${view.health.promise_active} promises are active. Follow dues before they age out.`,
      ),
      risk_level: view.health.cases_waiting > 40 ? "MEDIUM" : "LOW",
      next_action: "Review promises approaching their due date.",
      source: "fallback",
      cached: true,
      generated_at: view.generatedAt,
    },
  ];
}

function snapshotView(lastSyncedAt: string): DashboardView {
  const merchant: MerchantOption = {
    id: SNAPSHOT.merchant.list_id,
    merchant_name: SNAPSHOT.merchant.merchant_name,
    business_category: SNAPSHOT.merchant.business_category,
    timezone: SNAPSHOT.merchant.timezone,
  };
  const lift = buildLift(
    SNAPSHOT,
    SNAPSHOT.metrics.recovered_revenue,
    SNAPSHOT.metrics.recovery_rate,
  );
  const generatedAt = SNAPSHOT.metrics.updated_at;
  return {
    merchant,
    environment: environmentLabel(),
    dataSource: "simulator",
    lastSyncedAt,
    kpis: {
      revenue_at_risk: SNAPSHOT.metrics.revenue_at_risk,
      recovered_by_ai: SNAPSHOT.metrics.recovered_revenue,
      recovery_rate: SNAPSHOT.metrics.recovery_rate,
      ai_lift: SNAPSHOT.lift_recovered_revenue,
      pending_recovery_value: SNAPSHOT.recovery_summary.pending_recovery_value ?? 0,
      cases_waiting: SNAPSHOT.recovery_summary.open_cases,
    },
    funnel: SNAPSHOT.funnel,
    trend: SNAPSHOT.trend,
    failureReasons: SNAPSHOT.failure_reasons,
    lift,
    health: SNAPSHOT.health,
    insights: buildInsights({
      failureReasons: SNAPSHOT.failure_reasons,
      lift,
      health: SNAPSHOT.health,
      generatedAt,
    }),
    activity: SNAPSHOT.activity,
    topCustomers: SNAPSHOT.top_customers,
  };
}

function mapFailures(items: Array<{ failure_reason?: string | null; amount?: number }>): FailureReasonSlice[] {
  const buckets = new Map<string, FailureReasonSlice>();
  for (const key of ["INSUFFICIENT_FUNDS", "CARD_EXPIRED", "UPI_FAILURE", "MANDATE_REVOKED", "BANK_TIMEOUT", "OTHER"]) {
    buckets.set(key, {
      key,
      label: key === "OTHER" ? "Other" : FAILURE_LABELS[key] ?? key,
      count: 0,
      revenue_paise: 0,
    });
  }
  for (const item of items) {
    const raw = item.failure_reason ?? "UNKNOWN";
    const mapped = FAILURE_LABELS[raw] === "Other" || !FAILURE_LABELS[raw] ? "OTHER" : raw;
    const bucket = buckets.get(mapped) ?? buckets.get("OTHER");
    if (!bucket) {
      continue;
    }
    bucket.count += 1;
    bucket.revenue_paise += item.amount ?? 0;
  }
  return [...buckets.values()];
}

function mapTrend(payments: PaymentListItem[]): TrendPoint[] {
  const byDay = new Map<string, TrendPoint>();
  for (const payment of payments) {
    const stamp = payment.paid_at ?? payment.payment_time ?? payment.created_at;
    const day = stamp.slice(0, 10);
    const recovered =
      payment.payment_status === "CAPTURED" || payment.payment_status === "RECOVERED";
    if (!recovered) {
      continue;
    }
    const current = byDay.get(day) ?? {
      date: day,
      recovered_paise: 0,
      recovered_count: 0,
      baseline_paise: 0,
    };
    current.recovered_paise += payment.amount;
    current.recovered_count += 1;
    byDay.set(day, current);
  }
  return [...byDay.values()].sort((a, b) => a.date.localeCompare(b.date));
}

function mapQueue(items: RecoveryQueueItem[]): TopCustomerRow[] {
  return items.slice(0, 5).map((item) => {
    const diagnosis = item.diagnosed_reason ?? item.failure_reason ?? "UNKNOWN";
    return {
      recovery_case_id: item.recovery_case_id,
      customer_name: item.customer_name,
      customer_segment: item.customer_segment,
      plan_name: PLAN_BY_PAISE[item.amount] ?? "FitLife plan",
      amount: item.amount,
      diagnosis,
      strategy: STRATEGY_BY_REASON[diagnosis] ?? "Review case",
      recovery_status: item.recovery_status,
      priority_score: item.priority_score ?? 0,
      failed_at: item.failed_at,
    };
  });
}

function mapActivity(events: AuditEventItem[]): ActivityItem[] {
  return events.slice(0, 10).map((event) => ({
    event_type: event.event_type,
    summary: event.summary,
    timestamp: event.timestamp,
    actor: event.actor,
    recovery_case_id: event.recovery_case_id,
  }));
}

function funnelFromSummary(summary: RecoverySummary, atRisk: number): FunnelStage[] {
  const diagnosed = summary.recovered_cases + summary.stopped_cases + summary.escalated_cases + summary.open_cases + (summary.closed_cases ?? 0);
  const planned = summary.recovered_cases + summary.waiting_retry + summary.waiting_promise;
  return [
    { stage: "At Risk", count: Math.max(diagnosed, summary.open_cases + summary.recovered_cases), revenue_paise: atRisk },
    { stage: "Diagnosed", count: Math.max(diagnosed, 0), revenue_paise: atRisk },
    { stage: "Policy Approved", count: planned, revenue_paise: summary.recovered_revenue + (summary.pending_recovery_value ?? 0) },
    { stage: "Recovery Planned", count: planned, revenue_paise: summary.recovered_revenue + (summary.pending_recovery_value ?? 0) },
    { stage: "Recovered", count: summary.recovered_cases, revenue_paise: summary.recovered_revenue },
  ];
}

function healthFromSummary(summary: RecoverySummary, metrics: MerchantMetrics): DashboardView["health"] {
  const total = Math.max(
    summary.recovered_cases + summary.stopped_cases + summary.escalated_cases + summary.open_cases + (summary.closed_cases ?? 0),
    1,
  );
  const waiting = summary.waiting_retry + summary.waiting_promise;
  return {
    recovery_success_rate: metrics.recovery_rate || summary.recovery_rate,
    cases_waiting: waiting || summary.open_cases,
    cases_waiting_share: (waiting || summary.open_cases) / total,
    escalated: summary.escalated_cases,
    escalated_share: summary.escalated_cases / total,
    stopped: summary.stopped_cases,
    stopped_share: summary.stopped_cases / total,
    promise_active: summary.waiting_promise,
    promise_active_share: summary.waiting_promise / total,
    total_cases: total,
  };
}

export async function fetchMerchants(): Promise<MerchantOption[]> {
  try {
    const data = await getData<MerchantOption[]>("/merchants");
    if (data.length > 0) {
      return data;
    }
  } catch {
    /* fall through to snapshot */
  }
  return [
    {
      id: SNAPSHOT.merchant.list_id,
      merchant_name: SNAPSHOT.merchant.merchant_name,
      business_category: SNAPSHOT.merchant.business_category,
      timezone: SNAPSHOT.merchant.timezone,
    },
  ];
}

export interface LiveDashboardPayload {
  summary: MerchantSummary | null;
  metrics: MerchantMetrics | null;
  recovery: RecoverySummary | null;
  queue: RecoveryQueueItem[];
  failures: PaymentListItem[];
  payments: PaymentListItem[];
  activity: AuditEventItem[];
  live: boolean;
}

/** Fetch dashboard slices from existing v1 endpoints. Never mutates backend state. */
export async function fetchLiveDashboard(merchantId: string): Promise<LiveDashboardPayload> {
  const settled = await Promise.allSettled([
    getData<MerchantSummary>(`/merchants/${merchantId}/summary`),
    getData<MerchantMetrics>(`/merchants/${merchantId}/metrics`),
    getData<RecoverySummary>(`/recovery/summary?merchant_id=${merchantId}`),
    getPage<RecoveryQueueItem>(`/recovery/queue?merchant_id=${merchantId}&page=1&page_size=25`),
    getPage<PaymentListItem>(`/merchants/${merchantId}/failures?page=1&page_size=100`),
    getPage<PaymentListItem>(`/merchants/${merchantId}/payments?page=1&page_size=100`),
    getPage<AuditEventItem>("/audit/events?page=1&page_size=25"),
  ]);

  const value = <T>(index: number): T | null => {
    const result = settled[index];
    return result.status === "fulfilled" ? (result.value as T) : null;
  };

  const summary = value<MerchantSummary>(0);
  const metrics = value<MerchantMetrics>(1);
  const recovery = value<RecoverySummary>(2);
  const queuePage = value<{ data: RecoveryQueueItem[] }>(3);
  const failPage = value<{ data: PaymentListItem[] }>(4);
  const payPage = value<{ data: PaymentListItem[] }>(5);
  const auditPage = value<{ data: AuditEventItem[] }>(6);

  const allRejected = settled.every((item) => item.status === "rejected");
  if (allRejected) {
    const first = settled[0];
    throw first.status === "rejected" ? first.reason : new Error("Dashboard APIs unavailable");
  }

  const live =
    settled.some((item) => item.status === "fulfilled") &&
    Boolean(
      (metrics && (metrics.recovered_revenue > 0 || metrics.revenue_at_risk > 0)) ||
        (recovery && recovery.recovered_cases > 0) ||
        (queuePage && queuePage.data.length > 0),
    );

  return {
    summary,
    metrics,
    recovery,
    queue: queuePage?.data ?? [],
    failures: failPage?.data ?? [],
    payments: payPage?.data ?? [],
    activity: auditPage?.data ?? [],
    live,
  };
}

/** Merge live APIs onto the seed-42 FitLife snapshot when the ledger is empty. */
export function assembleDashboard(
  merchant: MerchantOption,
  live: LiveDashboardPayload | null,
  syncedAt: string,
): DashboardView {
  const base = snapshotView(syncedAt);
  if (!live?.live) {
    return {
      ...base,
      merchant,
      lastSyncedAt: syncedAt,
    };
  }

  const metrics = live.metrics ?? live.summary?.metrics ?? {
    merchant_id: merchant.id,
    revenue_at_risk: base.kpis.revenue_at_risk,
    recovered_revenue: base.kpis.recovered_by_ai,
    suppressed_revenue: 0,
    recovery_rate: base.kpis.recovery_rate,
    escalation_count: 0,
    policy_stop_count: 0,
    updated_at: syncedAt,
  };
  const recovery = live.recovery ?? SNAPSHOT.recovery_summary;
  const pending =
    recovery.pending_recovery_value ??
    SNAPSHOT.recovery_summary.pending_recovery_value ??
    0;
  const waiting = recovery.waiting_retry + recovery.waiting_promise || recovery.open_cases;
  const lift = buildLift(SNAPSHOT, metrics.recovered_revenue, metrics.recovery_rate);
  const failureReasons =
    live.failures.length >= 20 ? mapFailures(live.failures) : SNAPSHOT.failure_reasons;
  const trend = live.payments.length >= 20 ? mapTrend(live.payments) : SNAPSHOT.trend;
  const health = healthFromSummary(recovery, metrics);
  const generatedAt = metrics.updated_at ?? syncedAt;

  return {
    merchant: live.summary
      ? {
          id: merchant.id,
          merchant_name: live.summary.merchant.merchant_name,
          business_category: live.summary.merchant.business_category,
          timezone: live.summary.merchant.timezone,
        }
      : merchant,
    environment: environmentLabel(),
    dataSource: "live",
    lastSyncedAt: syncedAt,
    kpis: {
      revenue_at_risk: metrics.revenue_at_risk,
      recovered_by_ai: metrics.recovered_revenue,
      recovery_rate: metrics.recovery_rate,
      ai_lift: metrics.recovered_revenue - SNAPSHOT.baseline.recovered_revenue,
      pending_recovery_value: pending,
      cases_waiting: waiting,
    },
    funnel: funnelFromSummary(recovery, metrics.revenue_at_risk),
    trend,
    failureReasons,
    lift,
    health,
    insights: buildInsights({
      failureReasons,
      lift,
      health,
      generatedAt,
    }),
    activity: live.activity.length > 0 ? mapActivity(live.activity) : SNAPSHOT.activity,
    topCustomers: live.queue.length > 0 ? mapQueue(live.queue) : SNAPSHOT.top_customers,
  };
}
