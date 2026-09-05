import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { JsonHighlight } from "@/components/shared/JsonHighlight";
import { formatDateTime } from "@/lib/format";
import type { AuditEvent } from "@/types/recovery";

interface AuditEventCardProps {
  event: AuditEvent;
}

/** One collapsible audit row with actor, ids, and a pretty-printed JSON payload. */
export function AuditEventCard({ event }: AuditEventCardProps) {
  const [open, setOpen] = useState(false);
  const [jsonOpen, setJsonOpen] = useState(false);
  return (
    <article className="rounded-lg border border-border bg-surface">
      <button
        type="button"
        className="flex w-full items-start gap-2 px-3 py-2 text-left hover:bg-surface-hover"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        {open ? (
          <ChevronDown size={14} className="mt-0.5 shrink-0 text-muted" />
        ) : (
          <ChevronRight size={14} className="mt-0.5 shrink-0 text-muted" />
        )}
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium text-foreground">{event.summary}</p>
          <p className="mt-0.5 text-[11px] text-muted">
            {formatDateTime(event.created_at ?? event.timestamp)} · {event.actor}
            {event.actor_type ? ` · ${event.actor_type}` : ""}
            {event.status ? ` · ${event.status}` : ""}
          </p>
          <div className="mt-1 flex flex-wrap gap-1">
            {Boolean(event.details?.replay || event.details?.webhook_replay || event.metadata?.replay || event.metadata?.webhook_replay) ? (
              <span className="rounded-full bg-info-muted px-2 py-0.5 text-[10px] font-medium text-info">
                Webhook replay
              </span>
            ) : null}
            {event.details?.duplicate === true ? (
              <span className="rounded-full bg-ai-muted px-2 py-0.5 text-[10px] font-medium text-ai">
                Duplicate prevented
              </span>
            ) : null}
          </div>
          <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wide text-zinc-500">{event.event_type}</p>
        </div>
      </button>
      {open ? (
        <div className="space-y-1.5 border-t border-border px-3 py-2 text-[11px] text-muted">
          <p>
            Request ID <span className="break-all font-mono text-foreground">{event.request_id}</span>
          </p>
          <p>
            Correlation ID <span className="break-all font-mono text-foreground">{event.correlation_id}</span>
          </p>
          {event.policy_decision ? (
            <p>
              Policy <span className="text-foreground">{event.policy_decision}</span>
            </p>
          ) : null}
          <button
            type="button"
            className="mt-1 text-info hover:underline"
            onClick={() => setJsonOpen((value) => !value)}
            aria-expanded={jsonOpen}
          >
            {jsonOpen ? "Hide JSON payload" : "Expand JSON payload"}
          </button>
          {jsonOpen ? <JsonHighlight value={event.metadata ?? event.details} /> : null}
        </div>
      ) : null}
    </article>
  );
}
