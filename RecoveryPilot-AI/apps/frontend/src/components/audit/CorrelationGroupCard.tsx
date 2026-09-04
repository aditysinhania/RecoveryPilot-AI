import { useEffect, useState } from "react";
import { Check, ChevronDown, ChevronRight } from "lucide-react";
import { TimelineEventCard } from "@/components/audit/TimelineEventCard";
import { formatDateTime, titleCase } from "@/lib/format";
import { eventKey, formatLatency, toneClasses } from "@/lib/auditMap";
import type { AuditEventView, WorkflowGroup } from "@/types/audit";

interface CorrelationGroupCardProps {
  group: WorkflowGroup;
  selectedKey: string | null;
  defaultOpen?: boolean;
  onSelect: (event: AuditEventView) => void;
}

/** Expandable correlation workflow. Collapsed header is ~70px. */
export function CorrelationGroupCard({
  group,
  selectedKey,
  defaultOpen = false,
  onSelect,
}: CorrelationGroupCardProps) {
  const [open, setOpen] = useState(defaultOpen);
  const selectedHere = group.events.some((event) => eventKey(event) === selectedKey);

  useEffect(() => {
    if (defaultOpen) {
      setOpen(true);
    }
  }, [defaultOpen]);
  return (
    <article className={`overflow-hidden rounded-xl border ${selectedHere ? "border-info/40" : "border-border"} bg-surface`}>
      <button
        type="button"
        className="flex h-[70px] w-full items-center gap-2.5 px-3 text-left hover:bg-surface-hover"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? (
          <ChevronDown size={14} className="shrink-0 text-muted" />
        ) : (
          <ChevronRight size={14} className="shrink-0 text-muted" />
        )}
        <div className="min-w-0 flex-1">
          <p className="truncate font-mono text-[11px] text-info">{group.correlation_id}</p>
          <p className="mt-0.5 truncate text-[11px] text-muted">
            {group.event_count} events · {formatLatency(group.total_latency_ms)} · {formatDateTime(group.latest.timestamp)}
          </p>
        </div>
        <ol className="hidden shrink-0 items-center gap-1 sm:flex" aria-label="Workflow stages">
          {group.stages.map((stage) => {
            const filled = Boolean(stage.event);
            const tone = stage.event ? toneClasses(stage.event.tone).badge : "bg-zinc-800 text-zinc-500";
            return (
              <li
                key={stage.key}
                title={stage.label}
                className={`inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[9px] font-medium ${tone}`}
              >
                {filled ? <Check size={9} aria-hidden /> : null}
                {titleCase(stage.label)}
              </li>
            );
          })}
        </ol>
      </button>
      {open ? (
        <div className="space-y-1.5 border-t border-border px-2 py-2">
          {group.events.map((event) => (
            <TimelineEventCard
              key={eventKey(event)}
              event={event}
              selected={eventKey(event) === selectedKey}
              onSelect={onSelect}
            />
          ))}
        </div>
      ) : null}
    </article>
  );
}
