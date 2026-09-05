import { useMutation, useQueryClient } from "@tanstack/react-query";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatDateTime, titleCase } from "@/lib/format";
import { executionTimelineFor } from "@/lib/executionTimeline";
import { executeAction, replayAction, scheduleAction } from "@/services/actions";
import type { AuditEvent, CaseDrawerModel, TimelineEvent } from "@/types/recovery";

interface ExecutorCardProps {
  execution: CaseDrawerModel["execution"];
  recoveryCaseId: string;
  timeline: TimelineEvent[];
  audit: AuditEvent[];
}

const STEP_TONE: Record<string, string> = {
  complete: "bg-recovered-muted text-recovered",
  current: "bg-waiting-muted text-waiting",
  pending: "bg-zinc-800 text-zinc-500",
  skipped: "bg-zinc-800 text-zinc-500",
};

/** Live orchestrator snapshot as Scheduled → Sent → Delivered → Retry → Captured/Failed. */
export function ExecutorCard({ execution, recoveryCaseId, timeline, audit }: ExecutorCardProps) {
  const queryClient = useQueryClient();
  const invalidate = (): void => {
    void queryClient.invalidateQueries({ queryKey: ["recovery-case", recoveryCaseId] });
    void queryClient.invalidateQueries({ queryKey: ["action-status", recoveryCaseId] });
    void queryClient.invalidateQueries({ queryKey: ["recovery-queue"] });
    void queryClient.invalidateQueries({ queryKey: ["merchant-dashboard"] });
  };
  const execute = useMutation({
    mutationFn: () => executeAction(recoveryCaseId),
    onSuccess: invalidate,
  });
  const schedule = useMutation({
    mutationFn: () => scheduleAction(recoveryCaseId),
    onSuccess: invalidate,
  });
  const replay = useMutation({
    mutationFn: () => replayAction(execution.execution_id as string),
    onSuccess: invalidate,
  });
  const busy = execute.isPending || schedule.isPending || replay.isPending;
  const error = execute.error ?? schedule.error ?? replay.error;
  const liveStatus = execution.display_status || execution.status;
  const canAct = execution.live;
  const steps = executionTimelineFor(execution, timeline, audit);

  return (
    <section className="rounded-xl border border-border bg-surface-raised p-4" aria-labelledby="executor-heading">
      <div className="flex items-center justify-between gap-2">
        <h3 id="executor-heading" className="text-[11px] font-semibold uppercase tracking-wide text-muted">
          Execution
        </h3>
        <div className="flex flex-wrap items-center justify-end gap-1">
          <StatusBadge status={liveStatus} />
          {execution.action_chip ? <StatusBadge status={execution.action_chip} /> : null}
          {execution.webhook_replay || execution.status === "WEBHOOK_REPLAY" ? (
            <span className="rounded-full bg-info-muted px-2 py-0.5 text-[11px] font-medium text-info">
              Webhook replay
            </span>
          ) : null}
        </div>
      </div>

      <ol className="mt-4" aria-label="Execution timeline">
        {steps.map((step, index) => (
          <li key={step.key} className="relative flex gap-3 pb-4 last:pb-0">
            {index < steps.length - 1 ? (
              <span className="absolute left-[11px] top-6 h-[calc(100%-8px)] w-px bg-border" aria-hidden />
            ) : null}
            <span
              className={`relative z-10 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[10px] font-semibold ${STEP_TONE[step.state]}`}
              aria-hidden
            >
              {index + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-foreground">
                {step.label}
                {step.state === "skipped" ? (
                  <span className="ml-1.5 text-[10px] font-normal uppercase tracking-wide text-zinc-500">Skipped</span>
                ) : step.state === "current" ? (
                  <span className="ml-1.5 text-[10px] font-normal uppercase tracking-wide text-waiting">Current</span>
                ) : null}
              </p>
              <p className="mt-0.5 text-[11px] text-muted">
                {step.timestamp ? formatDateTime(step.timestamp) : step.state === "pending" ? "Not yet" : "—"}
              </p>
            </div>
          </li>
        ))}
      </ol>

      <dl className="mt-3 space-y-2 border-t border-border pt-3 text-xs">
        <div className="flex justify-between gap-3">
          <dt className="shrink-0 text-muted">Payment link</dt>
          <dd className="truncate text-right">
            {execution.payment_link ? (
              <a
                href={execution.payment_link}
                className="text-info hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                {execution.payment_link}
              </a>
            ) : (
              "—"
            )}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Retry attempts</dt>
          <dd className="tabular-nums">{execution.retry_attempts}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Delivery status</dt>
          <dd>{execution.delivery_status ? titleCase(execution.delivery_status) : "—"}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="shrink-0 text-muted">Execution ID</dt>
          <dd className="truncate font-mono text-[11px]" title={execution.execution_id ?? undefined}>
            {execution.execution_id ?? "—"}
          </dd>
        </div>
      </dl>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-lg bg-info px-2.5 py-1 text-[11px] font-medium text-white disabled:opacity-50"
          disabled={busy || !canAct}
          onClick={() => execute.mutate()}
        >
          Execute
        </button>
        <button
          type="button"
          className="rounded-lg border border-border px-2.5 py-1 text-[11px] font-medium text-foreground disabled:opacity-50"
          disabled={busy || !canAct}
          onClick={() => schedule.mutate()}
        >
          Schedule
        </button>
        <button
          type="button"
          className="rounded-lg border border-border px-2.5 py-1 text-[11px] font-medium text-foreground disabled:opacity-50"
          disabled={busy || !canAct || !execution.execution_id}
          onClick={() => replay.mutate()}
        >
          Replay
        </button>
      </div>
      {canAct ? null : (
        <p className="mt-2 text-[11px] text-muted">Sandbox execute is available when live APIs are connected.</p>
      )}
      {error ? (
        <p className="mt-2 text-[11px] text-blocked" role="alert">
          {error instanceof Error ? error.message : "Action failed"}
        </p>
      ) : null}
    </section>
  );
}
