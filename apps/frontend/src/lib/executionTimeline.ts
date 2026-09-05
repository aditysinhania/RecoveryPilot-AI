import type { AuditEvent, CaseDrawerModel, TimelineEvent } from "@/types/recovery";

export type ExecutionStepKey = "scheduled" | "sent" | "delivered" | "retry" | "outcome";
export type ExecutionStepState = "complete" | "current" | "pending" | "skipped";

export interface ExecutionStep {
  key: ExecutionStepKey;
  label: string;
  timestamp: string | null;
  state: ExecutionStepState;
}

function firstMatch(times: Array<string | null | undefined>): string | null {
  for (const value of times) {
    if (value) {
      return value;
    }
  }
  return null;
}

function timelineAt(events: TimelineEvent[], types: string[], summaryIncludes?: string): string | null {
  const match = events.find((event) => {
    if (!types.includes(event.event_type.toLowerCase())) {
      return false;
    }
    if (!summaryIncludes) {
      return true;
    }
    return event.summary.toLowerCase().includes(summaryIncludes);
  });
  return match?.occurred_at ?? null;
}

function auditAt(events: AuditEvent[], types: string[], summaryIncludes?: string): string | null {
  const match = events.find((event) => {
    if (!types.includes(event.event_type.toUpperCase())) {
      return false;
    }
    if (!summaryIncludes) {
      return true;
    }
    return event.summary.toLowerCase().includes(summaryIncludes);
  });
  return match?.timestamp ?? null;
}

function statusToken(execution: CaseDrawerModel["execution"]): string {
  return (execution.display_status || execution.status || "").toUpperCase();
}

/** Derive Scheduled → Sent → Delivered → Retry → Captured/Failed from live execution fields. */
export function executionTimelineFor(
  execution: CaseDrawerModel["execution"],
  timeline: TimelineEvent[],
  audit: AuditEvent[],
): ExecutionStep[] {
  const status = statusToken(execution);
  const delivery = (execution.delivery_status ?? "").toUpperCase();
  const retrying = status === "RETRYING";
  const trailCaptured = Boolean(
    timelineAt(timeline, ["recovered"]) ||
      timelineAt(timeline, ["webhook_update"], "captured") ||
      auditAt(audit, ["PAYMENT_CAPTURED"]),
  );
  const trailFailed = Boolean(
    timelineAt(timeline, ["stopped"]) || auditAt(audit, ["RECOVERY_STOPPED", "CASE_CLOSED"], "stop"),
  );
  const captured =
    status === "SUCCESS" ||
    status === "SUCCEEDED" ||
    status === "RECOVERED" ||
    status === "CAPTURED" ||
    trailCaptured;
  const failed =
    !captured &&
    (status === "FAILED" ||
      status === "EXPIRED" ||
      status === "CANCELLED" ||
      status === "DEAD_LETTER" ||
      execution.status === "FAILED" ||
      trailFailed);
  const sent =
    captured ||
    failed ||
    retrying ||
    status === "SENT" ||
    status === "RUNNING" ||
    status === "EXECUTED" ||
    delivery === "DELIVERED" ||
    delivery === "SENT" ||
    Boolean(execution.executed_time) ||
    Boolean(execution.payment_link);
  const retried = retrying || (execution.retry_attempts > 0 && (sent || captured || failed));
  const delivered =
    captured ||
    delivery === "DELIVERED" ||
    execution.action_chip === "Delivered" ||
    (sent && delivery !== "FAILED" && delivery !== "SKIPPED" && status !== "SCHEDULED" && status !== "RETRYING");
  const scheduled = Boolean(execution.scheduled_time) || sent || status === "SCHEDULED" || retried;

  const scheduledAt = firstMatch([
    execution.scheduled_time,
    timelineAt(timeline, ["action_scheduled"]),
    auditAt(audit, ["ACTION_SCHEDULED"]),
  ]);
  const sentAt = firstMatch([
    execution.executed_time,
    timelineAt(timeline, ["action_executed"]),
    auditAt(audit, ["ACTION_EXECUTED"]),
  ]);
  const deliveredAt = firstMatch([
    timelineAt(timeline, ["webhook_update"], "captured"),
    timelineAt(timeline, ["webhook_update"], "deliver"),
    delivery === "DELIVERED" || execution.action_chip === "Delivered" ? sentAt : null,
    auditAt(audit, ["PAYMENT_CAPTURED"]),
    auditAt(audit, ["ACTION_EXECUTED"], "deliver"),
  ]);
  const retryAt = retried
    ? firstMatch([
        status === "RETRYING" ? execution.scheduled_time : null,
        auditAt(audit, ["ACTION_SCHEDULED"], "retry"),
        timelineAt(timeline, ["action_scheduled"], "retry"),
        scheduledAt,
      ])
    : null;
  const outcomeAt = firstMatch([
    captured || failed ? sentAt : null,
    timelineAt(timeline, ["webhook_update", "recovered", "stopped"]),
    auditAt(audit, ["PAYMENT_CAPTURED", "RECOVERY_STOPPED", "CASE_CLOSED"]),
    execution.executed_time,
  ]);

  const outcomeLabel = failed && !captured ? "Failed" : "Captured";
  const retrySkipped = !retried && (captured || failed || (sent && !status.includes("RETRY")));

  const steps: ExecutionStep[] = [
    {
      key: "scheduled",
      label: "Scheduled",
      timestamp: scheduledAt,
      state: scheduled ? (sent || captured || failed || retried ? "complete" : "current") : "pending",
    },
    {
      key: "sent",
      label: "Sent",
      timestamp: sentAt,
      state: sent ? (delivered || retried || captured || failed ? "complete" : "current") : "pending",
    },
    {
      key: "delivered",
      label: "Delivered",
      timestamp: deliveredAt,
      state: delivery === "SKIPPED" ? "skipped" : delivered ? (retried || captured || failed ? "complete" : "current") : "pending",
    },
    {
      key: "retry",
      label: "Retry",
      timestamp: retryAt,
      state: retrySkipped ? "skipped" : retried ? (captured || failed ? "complete" : "current") : "pending",
    },
    {
      key: "outcome",
      label: outcomeLabel,
      timestamp: captured || failed ? outcomeAt : null,
      state: captured || failed ? "complete" : "pending",
    },
  ];

  if (status === "SCHEDULED" && !sent) {
    steps[0].state = "current";
  }
  return steps;
}
