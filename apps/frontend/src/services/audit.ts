import { getData, getPage } from "@/lib/api";
import {
  assembleComplianceInsights,
  assembleCorrelationReplay,
  apiActorFor,
  filterAuditEvents,
  isUuid,
  toAuditEventView,
} from "@/lib/auditMap";
import { SNAPSHOT } from "@/services/dashboard";
import { SNAPSHOT_QUEUE, snapshotCaseById } from "@/data/fitlifeQueue";
import type {
  AuditEventView,
  AuditFilters,
  AuditKpis,
  AuditPage,
  ComplianceInsights,
  CorrelationReplayView,
} from "@/types/audit";
import type { AuditEvent } from "@/types/recovery";

const FETCH_MS = 4_000;
const PAGE_SIZE = 50;

/** Seed-42 simulator knobs mirrored for cohort KPIs when /audit is down. */
const SEED_AUDIT_EVENTS = 1000;
const SEED_WEBHOOK_EVENTS = 500;
const SEED_WEBHOOK_DUPLICATE_RATE = 0.14;

function addMinutes(iso: string, minutes: number): string {
  const stamp = Date.parse(iso);
  if (Number.isNaN(stamp)) {
    return iso;
  }
  return new Date(stamp + minutes * 60_000).toISOString();
}

function snapshotCatalog(): AuditEventView[] {
  const rows: AuditEventView[] = [];
  for (const item of SNAPSHOT_QUEUE) {
    const model = snapshotCaseById(item.recovery_case_id);
    if (!model) {
      continue;
    }
    const mapped = model.audit.map((event) => {
      let actor = event.actor;
      if (event.actor === "diagnosis_engine") {
        actor = "Diagnosis Agent";
      } else if (event.actor === "policy_engine") {
        actor = "Policy Engine";
      } else if (event.actor === "planner_engine") {
        actor = "Scheduler";
      } else if (event.actor === "executor") {
        actor = "Recovery Executor";
      } else if (event.actor === "razorpay") {
        actor = "Razorpay Webhook";
      } else if (event.actor === "razorpay_webhook") {
        actor = "Razorpay Webhook";
      }
      return toAuditEventView({
        ...event,
        actor,
        correlation_id: event.recovery_case_id ?? event.correlation_id,
      });
    });
    rows.push(...mapped);

    const last = mapped[mapped.length - 1];
    const geminiAt = last ? addMinutes(last.timestamp, 1) : item.failed_at;
    rows.push(
      toAuditEventView({
        event_id: `aud-${item.recovery_case_id.slice(0, 8)}-gemini`,
        recovery_case_id: item.recovery_case_id,
        event_type: "DIAGNOSIS_COMPLETED",
        actor: "Gemini",
        actor_type: "AI_AGENT",
        timestamp: geminiAt,
        summary: model.explanations.compliance.body.slice(0, 140),
        request_id: `req-${item.recovery_case_id.slice(0, 8)}-gemini`,
        correlation_id: item.recovery_case_id,
        policy_decision: null,
        details: {
          model: "gemini-fallback",
          version: model.explanations.compliance.prompt_version,
          reason: model.explanations.compliance.body,
        },
      }),
    );

    if (item.recovery_status === "RECOVERED") {
      const captured = mapped.find((event) => event.display_type === "PAYMENT_CAPTURED") ?? last;
      if (captured) {
        rows.push(
          toAuditEventView({
            ...captured,
            event_id: `${captured.event_id ?? captured.request_id}-dup`,
            timestamp: addMinutes(captured.timestamp, 0.5),
            summary: "Webhook replay ignored (duplicate event id)",
            request_id: `${captured.request_id}-dup`,
            details: { ...captured.details, event: "payment.captured", duplicate: true, replay: true },
          }),
        );
      }
    }
    if (item.recovery_status === "WAITING_RETRY") {
      rows.push(
        toAuditEventView({
          event_id: `aud-${item.recovery_case_id.slice(0, 8)}-idem`,
          recovery_case_id: item.recovery_case_id,
          event_type: "ACTION_SKIPPED",
          actor: "Recovery Executor",
          actor_type: "SYSTEM",
          timestamp: addMinutes(last?.timestamp ?? geminiAt, 0.2),
          summary: "Duplicate execute ignored (idempotency key already used)",
          request_id: `req-${item.recovery_case_id.slice(0, 8)}-idem`,
          correlation_id: item.recovery_case_id,
          policy_decision: null,
          details: { duplicate: true, idempotency_key: true },
        }),
      );
    }
  }
  return rows.sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
}

let cachedCatalog: AuditEventView[] | null = null;

/** FitLife queue-catalog audit trail. Display map only. */
export function snapshotAuditCatalog(): AuditEventView[] {
  if (!cachedCatalog) {
    cachedCatalog = snapshotCatalog();
  }
  return cachedCatalog;
}

function paginate(items: AuditEventView[], page: number, pageSize: number, source: AuditPage["source"]): AuditPage {
  const total = items.length;
  const totalPages = Math.max(1, Math.ceil(total / pageSize) || 1);
  const safePage = Math.min(Math.max(1, page), totalPages);
  const start = (safePage - 1) * pageSize;
  return {
    items: items.slice(start, start + pageSize),
    page: safePage,
    page_size: pageSize,
    total,
    total_pages: totalPages,
    has_next: safePage < totalPages,
    has_previous: safePage > 1,
    source,
  };
}

function buildQuery(filters: AuditFilters, page: number, pageSize: number): string {
  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(pageSize));
  if (filters.correlationId.trim()) {
    params.set("correlation_id", filters.correlationId.trim());
  }
  if (isUuid(filters.caseId)) {
    params.set("recovery_case_id", filters.caseId.trim());
  }
  const actor = apiActorFor(filters.actor);
  if (actor) {
    params.set("actor", actor);
  }
  if (filters.eventType) {
    params.set("event_type", filters.eventType);
  }
  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }
  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }
  return params.toString();
}

function snapshotKpis(): AuditKpis {
  return {
    audit_events: SEED_AUDIT_EVENTS,
    correlation_replays: SNAPSHOT.counts.recovery_cases,
    policy_stops: SNAPSHOT.metrics.policy_stop_count,
    webhook_replays: SEED_WEBHOOK_EVENTS,
    duplicates_prevented: Math.round(SEED_WEBHOOK_EVENTS * SEED_WEBHOOK_DUPLICATE_RATE),
  };
}

async function countEvents(query: string): Promise<number | null> {
  const page = await getPage<AuditEvent>(`/audit/events?${query}`, FETCH_MS);
  return page.total ?? page.total_records ?? page.data?.length ?? null;
}

/** Cohort KPI strip. Uses typed /audit/events totals, then seed-42 snapshot. */
export async function fetchAuditKpis(): Promise<{ kpis: AuditKpis; source: "live" | "simulator" }> {
  try {
    const [all, stopped, captured, skipped] = await Promise.all([
      countEvents("page=1&page_size=1"),
      countEvents("page=1&page_size=1&event_type=RECOVERY_STOPPED"),
      countEvents("page=1&page_size=1&event_type=PAYMENT_CAPTURED"),
      countEvents("page=1&page_size=1&event_type=ACTION_SKIPPED"),
    ]);
    if (all == null || all === 0) {
      return { kpis: snapshotKpis(), source: "simulator" };
    }
    return {
      kpis: {
        audit_events: all,
        correlation_replays: SNAPSHOT.counts.recovery_cases,
        policy_stops: stopped ?? SNAPSHOT.metrics.policy_stop_count,
        webhook_replays: captured ?? SEED_WEBHOOK_EVENTS,
        duplicates_prevented:
          skipped && skipped > 0
            ? skipped
            : Math.round((captured ?? SEED_WEBHOOK_EVENTS) * SEED_WEBHOOK_DUPLICATE_RATE),
      },
      source: "live",
    };
  } catch {
    return { kpis: snapshotKpis(), source: "simulator" };
  }
}

/** Paginated explorer. Newest first. Falls back to the FitLife queue catalog. */
export async function fetchAuditPage(filters: AuditFilters, page: number): Promise<AuditPage> {
  try {
    const envelope = await getPage<AuditEvent>(`/audit/events?${buildQuery(filters, page, PAGE_SIZE)}`, FETCH_MS);
    const mapped = (envelope.data ?? []).map(toAuditEventView);
    const filtered = filters.severity
      ? filterAuditEvents(mapped, {
          ...filters,
          correlationId: "",
          caseId: "",
          actor: "",
          eventType: "",
          dateFrom: "",
          dateTo: "",
        })
      : mapped;
    const total = envelope.total ?? envelope.total_records ?? filtered.length;
    const totalPages = Math.max(1, envelope.total_pages ?? (Math.ceil(total / PAGE_SIZE) || 1));
    const serverFilters = Boolean(
      filters.correlationId.trim() ||
        isUuid(filters.caseId) ||
        filters.actor ||
        filters.eventType ||
        filters.dateFrom ||
        filters.dateTo,
    );
    if (mapped.length === 0 && total === 0 && !serverFilters) {
      return paginate(filterAuditEvents(snapshotAuditCatalog(), filters), page, PAGE_SIZE, "simulator");
    }
    return {
      items: filtered,
      page: envelope.page ?? page,
      page_size: envelope.page_size ?? PAGE_SIZE,
      total,
      total_pages: totalPages,
      has_next: envelope.has_next ?? page < totalPages,
      has_previous: envelope.has_previous ?? page > 1,
      source: "live",
    };
  } catch {
    return paginate(filterAuditEvents(snapshotAuditCatalog(), filters), page, PAGE_SIZE, "simulator");
  }
}

/** Compliance mix from the currently loaded explorer page plus catalog fallback. */
export function insightsFromPage(page: AuditPage): ComplianceInsights {
  const sample = page.source === "simulator" ? snapshotAuditCatalog() : page.items;
  return assembleComplianceInsights(sample);
}

/** GET /audit/correlation/{id}. Snapshot matches corr- prefix or case id. */
export async function fetchCorrelationReplay(correlationId: string): Promise<CorrelationReplayView | null> {
  const token = correlationId.trim();
  if (!token) {
    return null;
  }
  try {
    const data = await getData<{ correlation_id: string; event_count?: number; events: AuditEvent[] }>(
      `/audit/correlation/${encodeURIComponent(token)}`,
      FETCH_MS,
    );
    if (data.events?.length) {
      return assembleCorrelationReplay(data.correlation_id || token, data.events, "live");
    }
  } catch {
    /* snapshot below */
  }
  const matches = snapshotAuditCatalog().filter(
    (event) => event.correlation_id === token || event.recovery_case_id === token,
  );
  if (matches.length === 0) {
    return null;
  }
  return assembleCorrelationReplay(token, matches, "simulator");
}

export { PAGE_SIZE };
