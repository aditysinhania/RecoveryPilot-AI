import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatDateTime, titleCase } from "@/lib/format";
import type { CaseDrawerModel } from "@/types/recovery";

interface ExecutorCardProps {
  execution: CaseDrawerModel["execution"];
}

/** Read-only executor snapshot. No retry or action buttons. */
export function ExecutorCard({ execution }: ExecutorCardProps) {
  return (
    <section className="rounded-xl border border-border bg-surface-raised p-4" aria-labelledby="executor-heading">
      <div className="flex items-center justify-between gap-2">
        <h3 id="executor-heading" className="text-[11px] font-semibold uppercase tracking-wide text-muted">
          Executor
        </h3>
        <div className="flex flex-wrap items-center justify-end gap-1">
          <StatusBadge status={execution.status} />
          {execution.webhook_replay ? (
            <span className="rounded-full bg-info-muted px-2 py-0.5 text-[11px] font-medium text-info">
              Webhook replay
            </span>
          ) : null}
        </div>
      </div>
      <dl className="mt-3 space-y-2 text-xs">
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Execution type</dt>
          <dd className="truncate text-right">{titleCase(execution.type)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="shrink-0 text-muted">Execution ID</dt>
          <dd className="truncate font-mono text-[11px]" title={execution.execution_id ?? undefined}>
            {execution.execution_id ?? "—"}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="shrink-0 text-muted">Idempotency key</dt>
          <dd className="truncate font-mono text-[11px]" title={execution.idempotency_key ?? undefined}>
            {execution.idempotency_key ?? "—"}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Scheduled</dt>
          <dd>{execution.scheduled_time ? formatDateTime(execution.scheduled_time) : "—"}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Executed</dt>
          <dd>{execution.executed_time ? formatDateTime(execution.executed_time) : "—"}</dd>
        </div>
      </dl>
    </section>
  );
}
