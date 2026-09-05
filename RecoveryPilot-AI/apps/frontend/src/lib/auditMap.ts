import { isoDate, titleCase } from "@/lib/format";
import type {
  AuditEventType,
  AuditEventView,
  AuditFilters,
  AuditSeverity,
  AuditTone,
  ComplianceInsights,
  CorrelationReplayView,
  PolicyMixRow,
  ReplayStage,
  WorkflowGroup,
} from "@/types/audit";
import type { AuditEvent } from "@/types/recovery";

export const EMPTY_AUDIT_FILTERS: AuditFilters = {
  correlationId: "",
  caseId: "",
  actor: "",
  eventType: "",
  dateFrom: "",
  dateTo: "",
  severity: "",
};

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const TYPE_ALIASES: Record<string, AuditEventType> = {
  CASE_OPENED: "CASE_OPENED",
  PAYMENT_FAILED: "CASE_OPENED",
  DIAGNOSIS_COMPLETED: "DIAGNOSIS_COMPLETED",
  DIAGNOSIS_CREATED: "DIAGNOSIS_COMPLETED",
  POLICY_EVALUATED: "POLICY_EVALUATED",
  AUDIT: "POLICY_EVALUATED",
  ACTION_SCHEDULED: "ACTION_SCHEDULED",
  ACTION_EXECUTED: "ACTION_EXECUTED",
  ACTION_SKIPPED: "ACTION_SKIPPED",
  PROMISE_RECORDED: "PROMISE_RECORDED",
  PROMISE_FULFILLED: "PROMISE_FULFILLED",
  PROMISE_BROKEN: "PROMISE_BROKEN",
  PAYMENT_CAPTURED: "PAYMENT_CAPTURED",
  WEBHOOK_UPDATE: "PAYMENT_CAPTURED",
  RECOVERY_STOPPED: "RECOVERY_STOPPED",
  ESCALATED: "ESCALATED",
  CASE_CLOSED: "CASE_CLOSED",
  FINAL_OUTCOME: "CASE_CLOSED",
  GEMINI_EXPLANATION: "DIAGNOSIS_COMPLETED",
};

const ACTOR_API: Record<string, string> = {
  diagnosis: "Diagnosis Agent",
  policy: "POLICY_ENGINE",
  planner: "Scheduler",
  executor: "Recovery Executor",
  gemini: "Gemini",
  webhook: "Razorpay Webhook",
  customer: "CUSTOMER",
};

export const WORKFLOW_STEPS: { key: string; label: string; types: AuditEventType[] }[] = [
  { key: "diagnosis", label: "Diagnosis", types: ["DIAGNOSIS_COMPLETED"] },
  { key: "policy", label: "Policy", types: ["POLICY_EVALUATED", "RECOVERY_STOPPED", "ESCALATED"] },
  { key: "planner", label: "Planner", types: ["ACTION_SCHEDULED"] },
  { key: "executor", label: "Executor", types: ["ACTION_EXECUTED", "ACTION_SKIPPED"] },
  { key: "webhook", label: "Webhook", types: ["PAYMENT_CAPTURED"] },
  {
    key: "outcome",
    label: "Outcome",
    types: ["CASE_CLOSED", "PROMISE_FULFILLED", "PROMISE_BROKEN"],
  },
];

/** True when the token is a UUID the audit case route will accept. */
export function isUuid(value: string): boolean {
  return UUID_RE.test(value.trim());
}

/** Map live or snapshot event_type strings onto AuditEventType. */
export function normalizeEventType(eventType: string): AuditEventType {
  const key = eventType.trim().toUpperCase();
  return TYPE_ALIASES[key] ?? (key as AuditEventType);
}

/** Actor query value for GET /audit/events. Empty when the UI filter is All. */
export function apiActorFor(actor: string): string {
  return ACTOR_API[actor] ?? "";
}

function actorHaystack(event: AuditEvent): string {
  return `${event.actor} ${event.actor_type ?? ""} ${event.event_type}`.toLowerCase();
}

/** Display actor bucket used by the explorer filter and badges. */
export function displayActorFor(event: AuditEvent): AuditEventView["display_actor"] {
  const hay = actorHaystack(event);
  const type = normalizeEventType(event.event_type);
  if (hay.includes("gemini")) {
    return "gemini";
  }
  if (hay.includes("customer") || type.startsWith("PROMISE")) {
    return "customer";
  }
  if (hay.includes("webhook") || hay.includes("razorpay")) {
    return "webhook";
  }
  if (hay.includes("diagnos") || type === "DIAGNOSIS_COMPLETED") {
    return "diagnosis";
  }
  if (
    hay.includes("policy") ||
    type === "POLICY_EVALUATED" ||
    type === "RECOVERY_STOPPED" ||
    type === "ESCALATED"
  ) {
    return "policy";
  }
  if (hay.includes("planner") || hay.includes("scheduler") || type === "ACTION_SCHEDULED") {
    return "planner";
  }
  if (hay.includes("executor") || type === "ACTION_EXECUTED" || type === "ACTION_SKIPPED" || type === "CASE_CLOSED") {
    return "executor";
  }
  if (type === "PAYMENT_CAPTURED" || type === "CASE_OPENED") {
    return "webhook";
  }
  return "system";
}

function isWebhookReplay(event: AuditEvent): boolean {
  const details = event.details ?? {};
  return Boolean(details.replay || details.webhook_replay);
}

function isDuplicatePrevented(event: AuditEvent): boolean {
  const details = event.details ?? {};
  return Boolean(details.duplicate);
}

/** True when the event is a webhook replay, a duplicate, or both. */
export function isReplayOrDuplicate(event: AuditEvent): boolean {
  return isWebhookReplay(event) || isDuplicatePrevented(event);
}

/** Map a raw audit DTO into explorer view fields. */
export function toAuditEventView(event: AuditEvent): AuditEventView {
  return {
    ...event,
    details: event.details ?? {},
    display_actor: displayActorFor(event),
    display_type: normalizeEventType(event.event_type),
    severity: severityFor(event),
    tone: toneFor(event),
    duplicate: isDuplicatePrevented(event),
    webhook_replay: isWebhookReplay(event),
  };
}

/** Info / warning / error derived from type and policy. Not an API field. */
export function severityFor(event: AuditEvent): AuditSeverity {
  const type = normalizeEventType(event.event_type);
  const decision = (event.policy_decision ?? "").toUpperCase();
  if (
    type === "RECOVERY_STOPPED" ||
    type === "ESCALATED" ||
    type === "PROMISE_BROKEN" ||
    type === "ACTION_SKIPPED" ||
    decision === "STOP" ||
    decision === "DENY" ||
    decision === "ESCALATE"
  ) {
    return "error";
  }
  if (type === "CASE_OPENED" || type === "PROMISE_RECORDED" || decision === "WAIT") {
    return "warning";
  }
  return "info";
}

/** Badge tone: purple diagnosis/gemini, green success, orange wait, red stop, blue executor. */
export function toneFor(event: AuditEvent): AuditTone {
  const type = normalizeEventType(event.event_type);
  const actor = displayActorFor(event);
  const decision = (event.policy_decision ?? "").toUpperCase();
  if (type === "PAYMENT_CAPTURED" || type === "PROMISE_FULFILLED" || decision === "ALLOW") {
    if (type === "PAYMENT_CAPTURED" || type === "PROMISE_FULFILLED") {
      return "recovered";
    }
  }
  if (
    type === "RECOVERY_STOPPED" ||
    type === "ESCALATED" ||
    type === "PROMISE_BROKEN" ||
    decision === "STOP" ||
    decision === "DENY" ||
    decision === "ESCALATE"
  ) {
    return "blocked";
  }
  if (type === "CASE_OPENED" || type === "PROMISE_RECORDED" || type === "ACTION_SCHEDULED") {
    return "waiting";
  }
  if (actor === "diagnosis" || actor === "gemini" || actor === "policy") {
    return "ai";
  }
  return "info";
}

function matchesActor(event: AuditEventView, actor: string): boolean {
  if (!actor) {
    return true;
  }
  return event.display_actor === actor;
}

/** Client-side filter used for snapshot pages and severity (no API field). */
export function filterAuditEvents(events: AuditEventView[], filters: AuditFilters): AuditEventView[] {
  const correlation = filters.correlationId.trim().toLowerCase();
  const caseId = filters.caseId.trim().toLowerCase();
  return events.filter((event) => {
    if (correlation && !event.correlation_id.toLowerCase().includes(correlation)) {
      return false;
    }
    if (caseId) {
      const rowCase = (event.recovery_case_id ?? "").toLowerCase();
      if (!rowCase.includes(caseId)) {
        return false;
      }
    }
    if (!matchesActor(event, filters.actor)) {
      return false;
    }
    if (filters.eventType && event.display_type !== filters.eventType) {
      return false;
    }
    if (filters.severity && event.severity !== filters.severity) {
      return false;
    }
    const day = isoDate(event.timestamp);
    if (filters.dateFrom && day && day < filters.dateFrom) {
      return false;
    }
    if (filters.dateTo && day && day > filters.dateTo) {
      return false;
    }
    return true;
  });
}

/** Count of filters that are not empty. */
export function activeAuditFilterCount(filters: AuditFilters): number {
  return Object.values(filters).filter((value) => value.trim().length > 0).length;
}

function policyKey(event: AuditEventView): string | null {
  const decision = (event.policy_decision ?? "").toUpperCase();
  if (decision === "ALLOW" || decision === "STOP" || decision === "DENY" || decision === "ESCALATE") {
    return decision;
  }
  if (event.display_type === "RECOVERY_STOPPED") {
    return "STOP";
  }
  if (event.display_type === "ESCALATED" || event.display_type === "PROMISE_BROKEN") {
    return "ESCALATE";
  }
  return null;
}

/** Roll policy / webhook / idempotency counts from the loaded event sample. */
export function assembleComplianceInsights(events: AuditEventView[]): ComplianceInsights {
  const counts: Record<string, number> = { ALLOW: 0, STOP: 0, DENY: 0, ESCALATE: 0 };
  const keys = new Set<string>();
  let webhook = 0;
  let duplicates = 0;
  let skipped = 0;
  let escalations = 0;
  for (const event of events) {
    const bucket = policyKey(event);
    if (bucket) {
      counts[bucket] += 1;
    }
    if (event.display_type === "PAYMENT_CAPTURED" || event.display_actor === "webhook") {
      webhook += 1;
    }
    if (event.duplicate) {
      duplicates += 1;
    }
    if (event.display_type === "ACTION_SKIPPED") {
      skipped += 1;
    }
    if (event.display_type === "ESCALATED" || event.policy_decision === "ESCALATE") {
      escalations += 1;
    }
    if (event.recovery_case_id) {
      keys.add(event.recovery_case_id);
    }
  }
  const policy: PolicyMixRow[] = (["ALLOW", "STOP", "DENY", "ESCALATE"] as const).map((key) => ({
    key,
    label: titleCase(key),
    count: counts[key],
  }));
  const allow = counts.ALLOW;
  const stop = counts.STOP;
  return {
    policy,
    allow,
    stop,
    deny: counts.DENY,
    escalate: counts.ESCALATE,
    stop_allow_ratio: allow > 0 ? stop / allow : stop > 0 ? 1 : 0,
    escalations,
    webhook_replays: webhook,
    duplicates_prevented: duplicates,
    idempotency_keys: keys.size,
    skipped_actions: skipped,
  };
}

function firstOfType(events: AuditEventView[], types: AuditEventType[]): AuditEventView | null {
  return events.find((event) => types.includes(event.display_type as AuditEventType)) ?? null;
}

function latencyMs(from: AuditEventView | null, to: AuditEventView | null): number | null {
  if (!from || !to) {
    return null;
  }
  const start = Date.parse(from.timestamp);
  const end = Date.parse(to.timestamp);
  if (Number.isNaN(start) || Number.isNaN(end) || end < start) {
    return null;
  }
  return end - start;
}

/** Ordered workflow stages plus per-hop latency for one correlation id. */
export function assembleCorrelationReplay(
  correlationId: string,
  events: AuditEvent[],
  source: "live" | "simulator",
): CorrelationReplayView {
  const ordered = [...events]
    .map(toAuditEventView)
    .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp) || a.display_type.localeCompare(b.display_type));
  const stages: ReplayStage[] = [];
  let previous: AuditEventView | null = null;
  const pipeline = [
    { key: "payment", label: "Payment Failed", types: ["CASE_OPENED"] as AuditEventType[] },
    ...WORKFLOW_STEPS,
  ];
  for (const stage of pipeline) {
    const event = firstOfType(ordered, stage.types);
    stages.push({
      key: stage.key,
      label: stage.label,
      event,
      latency_ms: event ? latencyMs(previous, event) : null,
    });
    if (event) {
      previous = event;
    }
  }
  const first = ordered[0] ?? null;
  const last = ordered[ordered.length - 1] ?? null;
  return {
    correlation_id: correlationId,
    event_count: ordered.length,
    events: ordered,
    stages,
    total_latency_ms: latencyMs(first, last) ?? 0,
    source,
  };
}

/** Milliseconds to a compact hop label (4m, 12.0s). */
export function formatLatency(ms: number | null): string {
  if (ms == null || Number.isNaN(ms)) {
    return "—";
  }
  if (ms < 1000) {
    return `${Math.round(ms)}ms`;
  }
  if (ms < 60_000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }
  if (ms < 3_600_000) {
    const minutes = Math.floor(ms / 60_000);
    const seconds = Math.round((ms % 60_000) / 1000);
    return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
  }
  const hours = Math.floor(ms / 3_600_000);
  const minutes = Math.round((ms % 3_600_000) / 60_000);
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
}

/** Group a page of events into correlation workflows, newest group first. */
export function groupByCorrelation(events: AuditEventView[]): WorkflowGroup[] {
  const buckets = new Map<string, AuditEventView[]>();
  for (const event of events) {
    const key = event.correlation_id || event.recovery_case_id || event.request_id;
    const list = buckets.get(key) ?? [];
    list.push(event);
    buckets.set(key, list);
  }
  return [...buckets.entries()]
    .map(([correlation_id, items]) => {
      const newestFirst = [...items].sort(
        (a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp),
      );
      const replay = assembleCorrelationReplay(correlation_id, items, "simulator");
      return {
        correlation_id,
        events: newestFirst,
        latest: newestFirst[0],
        event_count: items.length,
        stages: replay.stages.filter((stage) => stage.key !== "payment"),
        total_latency_ms: replay.total_latency_ms,
      };
    })
    .sort((a, b) => Date.parse(b.latest.timestamp) - Date.parse(a.latest.timestamp));
}

/** Stable key for selecting one explorer event. */
export function eventKey(event: AuditEventView): string {
  return `${event.event_id ?? event.request_id}-${event.timestamp}`;
}

/** Milliseconds between two events, or null. */
export function hopLatency(from: AuditEventView | null, to: AuditEventView | null): number | null {
  return latencyMs(from, to);
}

/** Badge classes for the five compliance colors. */
export function toneClasses(tone: AuditTone): { icon: string; badge: string } {
  if (tone === "ai") {
    return { icon: "text-ai bg-ai-muted", badge: "bg-ai-muted text-ai" };
  }
  if (tone === "recovered") {
    return { icon: "text-recovered bg-recovered-muted", badge: "bg-recovered-muted text-recovered" };
  }
  if (tone === "waiting") {
    return { icon: "text-waiting bg-waiting-muted", badge: "bg-waiting-muted text-waiting" };
  }
  if (tone === "blocked") {
    return { icon: "text-blocked bg-blocked-muted", badge: "bg-blocked-muted text-blocked" };
  }
  return { icon: "text-info bg-info-muted", badge: "bg-info-muted text-info" };
}
