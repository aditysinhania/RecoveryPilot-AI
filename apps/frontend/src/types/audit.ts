import type { AuditEvent } from "@/types/recovery";

export const AUDIT_ACTORS = [
  "diagnosis",
  "policy",
  "planner",
  "executor",
  "gemini",
  "webhook",
  "customer",
] as const;

export const AUDIT_EVENT_TYPES = [
  "CASE_OPENED",
  "DIAGNOSIS_COMPLETED",
  "POLICY_EVALUATED",
  "ACTION_SCHEDULED",
  "ACTION_EXECUTED",
  "ACTION_SKIPPED",
  "PROMISE_RECORDED",
  "PROMISE_FULFILLED",
  "PROMISE_BROKEN",
  "PAYMENT_CAPTURED",
  "RECOVERY_STOPPED",
  "ESCALATED",
  "CASE_CLOSED",
] as const;

export const AUDIT_SEVERITIES = ["info", "warning", "error"] as const;

export type AuditActor = (typeof AUDIT_ACTORS)[number];
export type AuditEventType = (typeof AUDIT_EVENT_TYPES)[number];
export type AuditSeverity = (typeof AUDIT_SEVERITIES)[number];
export type AuditTone = "ai" | "recovered" | "waiting" | "blocked" | "info";

export interface AuditFilters {
  correlationId: string;
  caseId: string;
  actor: string;
  eventType: string;
  dateFrom: string;
  dateTo: string;
  severity: string;
}

export interface AuditEventView extends AuditEvent {
  display_actor: AuditActor | "system";
  display_type: string;
  severity: AuditSeverity;
  tone: AuditTone;
  duplicate: boolean;
  webhook_replay: boolean;
}

export interface AuditPage {
  items: AuditEventView[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  source: "live" | "simulator";
}

export interface AuditKpis {
  audit_events: number;
  correlation_replays: number;
  policy_stops: number;
  webhook_replays: number;
  duplicates_prevented: number;
}

export interface PolicyMixRow {
  key: string;
  label: string;
  count: number;
}

export interface ComplianceInsights {
  policy: PolicyMixRow[];
  allow: number;
  stop: number;
  deny: number;
  escalate: number;
  stop_allow_ratio: number;
  escalations: number;
  webhook_replays: number;
  duplicates_prevented: number;
  idempotency_keys: number;
  skipped_actions: number;
}

export interface ReplayStage {
  key: string;
  label: string;
  event: AuditEventView | null;
  latency_ms: number | null;
}

export interface CorrelationReplayView {
  correlation_id: string;
  event_count: number;
  events: AuditEventView[];
  stages: ReplayStage[];
  total_latency_ms: number;
  source: "live" | "simulator";
}

export interface WorkflowGroup {
  correlation_id: string;
  events: AuditEventView[];
  latest: AuditEventView;
  event_count: number;
  stages: ReplayStage[];
  total_latency_ms: number;
}

export interface AuditExplorerView {
  kpis: AuditKpis;
  page: AuditPage;
  insights: ComplianceInsights;
  replay: CorrelationReplayView | null;
  sample_label: string;
}
