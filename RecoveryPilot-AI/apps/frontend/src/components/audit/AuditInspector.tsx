import { Link } from "react-router-dom";
import { CorrelationReplay } from "@/components/audit/CorrelationReplay";
import { JsonPayloadViewer } from "@/components/audit/JsonPayloadViewer";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatDateTime, formatPercent, titleCase } from "@/lib/format";
import { eventIcon } from "@/components/audit/TimelineEventCard";
import { formatLatency, hopLatency, toneClasses } from "@/lib/auditMap";
import type { AuditEventView, ComplianceInsights, CorrelationReplayView } from "@/types/audit";

interface AuditInspectorProps {
  event: AuditEventView | null;
  replay: CorrelationReplayView | null;
  replayLoading: boolean;
  insights: ComplianceInsights | null;
}

function hopFor(event: AuditEventView, replay: CorrelationReplayView | null): number | null {
  if (!replay) {
    return null;
  }
  const index = replay.events.findIndex(
    (item) => item.request_id === event.request_id && item.timestamp === event.timestamp,
  );
  if (index <= 0) {
    return null;
  }
  return hopLatency(replay.events[index - 1] ?? null, event);
}

/** Sticky right inspector. Fills with the selected event — no empty chart column. */
export function AuditInspector({ event, replay, replayLoading, insights }: AuditInspectorProps) {
  if (!event) {
    return (
      <aside className="rounded-xl border border-dashed border-border bg-surface p-4">
        <h2 className="text-sm font-semibold">Inspector</h2>
        <EmptyState
          compact
          title="Select an event"
          description="Click a row in a workflow card. Replay and JSON load here."
        />
      </aside>
    );
  }
  const Icon = eventIcon(event);
  const tones = toneClasses(event.tone);
  const hop = hopFor(event, replay);
  return (
    <aside className="space-y-3 rounded-xl border border-border bg-surface p-3 shadow-[var(--shadow-card)]">
      <div className="flex items-start gap-2.5">
        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${tones.icon}`}>
          <Icon size={14} aria-hidden />
        </span>
        <div className="min-w-0">
          <p className="text-xs font-semibold text-foreground">{event.summary}</p>
          <p className="mt-0.5 text-[11px] text-muted">{formatDateTime(event.timestamp)}</p>
          <div className="mt-1.5 flex flex-wrap gap-1">
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${tones.badge}`}>
              {titleCase(event.display_actor)}
            </span>
            <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] font-medium text-muted">
              {titleCase(event.display_type)}
            </span>
            {event.policy_decision ? (
              <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] font-medium text-foreground">
                {event.policy_decision}
              </span>
            ) : null}
            {event.duplicate ? (
              <span className="rounded-full bg-ai-muted px-2 py-0.5 text-[10px] font-medium text-ai">Duplicate</span>
            ) : null}
          </div>
        </div>
      </div>

      <dl className="grid gap-1.5 text-[11px]">
        <div>
          <dt className="text-zinc-500">Request ID</dt>
          <dd className="break-all font-mono text-foreground">{event.request_id}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Correlation ID</dt>
          <dd className="break-all font-mono text-info">{event.correlation_id}</dd>
        </div>
        <div>
          <dt className="text-zinc-500">Latency from previous</dt>
          <dd className="tabular-nums text-foreground">{formatLatency(hop)}</dd>
        </div>
        {event.recovery_case_id ? (
          <div>
            <dt className="text-zinc-500">Case</dt>
            <dd>
              <Link className="text-info hover:underline" to={`/recovery-queue?case=${event.recovery_case_id}`}>
                Open in queue
              </Link>
            </dd>
          </div>
        ) : null}
      </dl>

      <section>
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted">Replay flow</h3>
        <div className="mt-1.5">
          <CorrelationReplay replay={replay} loading={replayLoading} />
        </div>
      </section>

      {insights ? (
        <section>
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted">Compliance</h3>
          <dl className="mt-1.5 grid grid-cols-2 gap-1.5 text-[11px]">
            <div>
              <dt className="text-zinc-500">STOP vs ALLOW</dt>
              <dd className="tabular-nums">{formatPercent(insights.stop_allow_ratio)}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Escalations</dt>
              <dd className="tabular-nums text-blocked">{insights.escalations}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Duplicates</dt>
              <dd className="tabular-nums text-ai">{insights.duplicates_prevented}</dd>
            </div>
            <div>
              <dt className="text-zinc-500">Idempotency keys</dt>
              <dd className="tabular-nums">{insights.idempotency_keys}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      <section>
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted">JSON payload</h3>
        <JsonPayloadViewer value={event.details} />
      </section>
    </aside>
  );
}
