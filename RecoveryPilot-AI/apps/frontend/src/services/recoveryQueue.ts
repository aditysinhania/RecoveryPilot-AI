import { getData, getPage } from "@/lib/api";
import {
  allowedChannelsFor,
  applyClientFilters,
  blockedChannelsFor,
  buildExplanations,
  communicationCostPaise,
  contributorsFor,
  decisionPriority,
  evaluatedRulesFor,
  evidenceFor,
  fallbackStrategyFor,
  hasActiveFilters,
  nextPaydayIso,
  plannerStrategyFor,
  planNameFor,
  policyStatusFor,
  recoveryProbability,
  toQueueRow,
  triggeredRulesFor,
} from "@/lib/recoveryMap";
import { formatPaise, isoDate } from "@/lib/format";
import {
  FITLIFE_AS_OF,
  SNAPSHOT_QUEUE,
  SNAPSHOT_SUMMARY,
  snapshotCaseById,
} from "@/data/fitlifeQueue";
import type { RecoverySummary } from "@/types/dashboard";
import type {
  AuditEvent,
  CaseDrawerModel,
  PolicyRow,
  QueuePage,
  QueueRow,
  QueueSortKey,
  RecoveryCaseDetail,
  RecoveryQueueFilters,
  RecoveryQueueItem,
  RecoveryQueueSummary,
  TimelineEvent,
} from "@/types/recovery";

const FETCH_MS = 4_000;

export interface QueueQuery {
  merchantId: string;
  filters: RecoveryQueueFilters;
  page: number;
  pageSize: number;
  sortKey: QueueSortKey;
  sortDir: "asc" | "desc";
}

function compareRows(a: QueueRow, b: QueueRow, key: QueueSortKey, dir: "asc" | "desc"): number {
  const sign = dir === "asc" ? 1 : -1;
  const left = a[key];
  const right = b[key];
  if (typeof left === "number" && typeof right === "number") {
    return (left - right) * sign;
  }
  return String(left ?? "").localeCompare(String(right ?? ""), "en-IN") * sign;
}

function paginate(rows: QueueRow[], page: number, pageSize: number, source: QueuePage["source"]): QueuePage {
  const total = rows.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const start = (safePage - 1) * pageSize;
  return {
    items: rows.slice(start, start + pageSize),
    page: safePage,
    page_size: pageSize,
    total,
    total_pages: totalPages,
    has_next: safePage < totalPages,
    has_previous: safePage > 1,
    source,
  };
}

function serverQuery(filters: RecoveryQueueFilters, merchantId: string, page: number, pageSize: number): string {
  const params = new URLSearchParams();
  if (merchantId) {
    params.set("merchant_id", merchantId);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.diagnosis) {
    params.set("failure_reason", filters.diagnosis);
  }
  if (filters.segment) {
    params.set("customer_segment", filters.segment);
  }
  if (filters.priority) {
    params.set("priority", filters.priority);
  }
  if (filters.paymentMethod) {
    params.set("payment_method", filters.paymentMethod);
  }
  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  return `/recovery/queue?${params.toString()}`;
}

function chipsFromRows(rows: QueueRow[], fallback: RecoveryQueueSummary): RecoveryQueueSummary {
  const asOf = FITLIFE_AS_OF.slice(0, 10);
  const recoveredToday = rows.filter(
    (row) => row.recovery_status === "RECOVERED" && isoDate(row.last_updated) === asOf,
  ).length;
  const open = rows.filter((row) =>
    ["OPEN", "DIAGNOSED", "WAITING_RETRY", "WAITING_PROMISE"].includes(row.recovery_status),
  );
  if (rows.length === 0) {
    return { ...fallback, recovered_today: 0 };
  }
  return {
    open_cases: open.length,
    recovered_cases: rows.filter((row) => row.recovery_status === "RECOVERED").length,
    stopped_cases: rows.filter((row) => row.recovery_status === "STOPPED" || row.recovery_status === "CLOSED").length,
    escalated_cases: rows.filter((row) => row.recovery_status === "ESCALATED").length,
    waiting_retry: rows.filter((row) => row.recovery_status === "WAITING_RETRY").length,
    waiting_promise: rows.filter((row) => row.recovery_status === "WAITING_PROMISE").length,
    total_revenue_at_risk: open.reduce((sum, row) => sum + row.amount, 0),
    recovered_revenue: rows
      .filter((row) => row.recovery_status === "RECOVERED")
      .reduce((sum, row) => sum + row.amount, 0),
    recovery_rate: fallback.recovery_rate,
    recovered_today: recoveredToday,
  };
}

function snapshotFiltered(filters: RecoveryQueueFilters): QueueRow[] {
  return applyClientFilters(SNAPSHOT_QUEUE, filters);
}

/** Load the recovery queue. Live APIs overlay the FitLife seed-42 catalog. */
export async function fetchRecoveryQueue(query: QueueQuery): Promise<{
  page: QueuePage;
  summary: RecoveryQueueSummary;
  source: "live" | "simulator";
}> {
  try {
    const envelope = await getPage<RecoveryQueueItem>(
      serverQuery(query.filters, query.merchantId, 1, 100),
      FETCH_MS,
    );
    const liveRows = applyClientFilters((envelope.data ?? []).map(toQueueRow), query.filters);
    if (liveRows.length === 0 && (envelope.total ?? 0) === 0) {
      throw new Error("empty-live-queue");
    }
    const sorted = [...liveRows].sort((a, b) => compareRows(a, b, query.sortKey, query.sortDir));
    let summary: RecoveryQueueSummary = { ...SNAPSHOT_SUMMARY };
    try {
      const liveSummary = await getData<RecoverySummary>(
        `/recovery/summary?merchant_id=${encodeURIComponent(query.merchantId)}`,
        FETCH_MS,
      );
      summary = {
        ...SNAPSHOT_SUMMARY,
        ...liveSummary,
        recovered_today: SNAPSHOT_SUMMARY.recovered_today,
      };
    } catch {
      summary = SNAPSHOT_SUMMARY;
    }
    const filteredSummary = hasActiveFilters(query.filters) ? chipsFromRows(sorted, summary) : {
      ...summary,
      recovered_today: chipsFromRows(sorted, summary).recovered_today,
    };
    return {
      page: paginate(sorted, query.page, query.pageSize, "live"),
      summary: filteredSummary,
      source: "live",
    };
  } catch {
    const sorted = [...snapshotFiltered(query.filters)].sort((a, b) =>
      compareRows(a, b, query.sortKey, query.sortDir),
    );
    const summary = hasActiveFilters(query.filters)
      ? chipsFromRows(sorted, SNAPSHOT_SUMMARY)
      : {
          ...SNAPSHOT_SUMMARY,
          recovered_today: chipsFromRows(sorted, SNAPSHOT_SUMMARY).recovered_today,
        };
    return {
      page: paginate(sorted, query.page, query.pageSize, "simulator"),
      summary,
      source: "simulator",
    };
  }
}

function webhookReplay(timeline: TimelineEvent[], action: RecoveryCaseDetail["latest_action"]): boolean {
  if (action?.action_metadata && action.action_metadata.webhook_replay === true) {
    return true;
  }
  return timeline.some((event) => {
    if (event.event_type !== "webhook_update") {
      return false;
    }
    return Boolean(event.details.duplicate || event.details.replay || event.details.webhook_replay);
  });
}

function enrichCase(
  detail: RecoveryCaseDetail,
  timeline: TimelineEvent[],
  audit: AuditEvent[],
  policyRows: PolicyRow[],
  source: "live" | "simulator",
): CaseDrawerModel {
  const reason = detail.diagnosed_reason ?? detail.payment.failure_reason ?? "UNKNOWN";
  const strategy = plannerStrategyFor(reason, detail.recovery_status);
  const fallback = fallbackStrategyFor(strategy);
  const decision =
    policyRows.find((row) => row.decision !== "ALLOW")?.decision ??
    policyRows[0]?.decision ??
    policyStatusFor(detail.recovery_status);
  const allowed = allowedChannelsFor(strategy, decision);
  const blocked = blockedChannelsFor(allowed);
  const scheduled = detail.latest_action?.scheduled_time ?? nextPaydayIso(detail.payment.created_at);
  const probability = recoveryProbability(
    detail.customer.customer_segment,
    reason,
    detail.recovery_status,
  );
  const diagnosisEvent = timeline.find((event) => event.event_type === "diagnosis_created");
  const confidence =
    detail.ai_confidence ??
    (typeof diagnosisEvent?.details.confidence === "number" ? diagnosisEvent.details.confidence : 0);
  return {
    case: detail,
    diagnosis: {
      primary: reason,
      confidence,
      evidence: evidenceFor(reason),
      triggered_rules: triggeredRulesFor(reason),
      version: detail.diagnosis_version ?? "1.0.0",
      model: detail.diagnosis_model ?? "recovery_diagnosis_v1",
      contributors: contributorsFor(reason),
    },
    policy: {
      decision,
      decision_priority: decisionPriority(decision),
      reasons: policyRows.map((row) => row.reason).filter(Boolean),
      allowed_channels: allowed,
      blocked_channels: blocked,
      cooldown_until: detail.recovery_status.startsWith("WAITING") ? scheduled : null,
      evaluated_rules:
        policyRows.length > 0
          ? policyRows.map((row) => ({
              policy_name: row.policy_name,
              result: row.decision,
              reason: row.reason,
            }))
          : evaluatedRulesFor(decision),
    },
    planner: {
      primary_strategy: strategy,
      fallback_strategy: fallback,
      scheduled_time: scheduled,
      recovery_probability: probability,
      expected_recovered_value: Math.round(detail.payment.amount * probability),
      estimated_communication_cost: communicationCostPaise(allowed),
    },
    execution: {
      status: detail.latest_action?.execution_status ?? "PENDING",
      type: detail.latest_action?.action_type ?? "NONE",
      idempotency_key: detail.payment.idempotency_key ?? null,
      execution_id: detail.latest_action?.id ?? null,
      scheduled_time: detail.latest_action?.scheduled_time ?? null,
      executed_time: detail.latest_action?.executed_time ?? null,
      webhook_replay: webhookReplay(timeline, detail.latest_action),
    },
    explanations: buildExplanations({
      name: detail.customer.full_name,
      plan: detail.subscription?.subscription_name ?? planNameFor(detail.payment.amount),
      amountLabel: formatPaise(detail.payment.amount),
      diagnosis: reason,
      decision,
      strategy,
      status: detail.recovery_status,
      generatedAt: detail.updated_at,
      cached: source === "simulator",
    }),
    timeline,
    audit,
    source,
  };
}

async function loadAudit(recoveryCaseId: string): Promise<AuditEvent[]> {
  try {
    const timeline = await getData<{ events?: AuditEvent[] }>(`/audit/cases/${recoveryCaseId}`, FETCH_MS);
    if (timeline.events?.length) {
      return timeline.events;
    }
  } catch {
    /* fall through to the events explorer */
  }
  const page = await getPage<AuditEvent>(
    `/audit/events?recovery_case_id=${encodeURIComponent(recoveryCaseId)}&page=1&page_size=50`,
    FETCH_MS,
  );
  return page.data ?? [];
}

/** Lazy-load one case drawer. Cached by recovery_case_id in TanStack Query. */
export async function fetchRecoveryCase(recoveryCaseId: string): Promise<CaseDrawerModel> {
  try {
    const [detail, timeline, policyRows] = await Promise.all([
      getData<RecoveryCaseDetail>(`/recovery/cases/${recoveryCaseId}`, FETCH_MS),
      getData<TimelineEvent[]>(`/recovery/cases/${recoveryCaseId}/timeline`, FETCH_MS),
      getData<PolicyRow[]>(`/audit/cases/${recoveryCaseId}/policy`, FETCH_MS).catch(() => []),
    ]);
    const audit = await loadAudit(recoveryCaseId).catch(() => []);
    return enrichCase(detail, timeline ?? [], audit, policyRows ?? [], "live");
  } catch {
    const snapshot = snapshotCaseById(recoveryCaseId);
    if (!snapshot) {
      throw new Error("Case not found");
    }
    return snapshot;
  }
}

export function emptyQueuePage(pageSize: number): QueuePage {
  return {
    items: [],
    page: 1,
    page_size: pageSize,
    total: 0,
    total_pages: 1,
    has_next: false,
    has_previous: false,
    source: "simulator",
  };
}
