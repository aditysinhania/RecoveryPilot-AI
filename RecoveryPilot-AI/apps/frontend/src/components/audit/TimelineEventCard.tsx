import { Link } from "react-router-dom";
import {
  AlertTriangle,
  Ban,
  Brain,
  CalendarClock,
  CheckCircle2,
  Cpu,
  Shield,
  Sparkles,
  User,
  Wallet,
  Webhook,
  type LucideIcon,
} from "lucide-react";
import { formatDateTime, titleCase } from "@/lib/format";
import { eventKey, toneClasses } from "@/lib/auditMap";
import type { AuditEventView } from "@/types/audit";

const ICONS: Record<string, LucideIcon> = {
  diagnosis: Brain,
  policy: Shield,
  planner: CalendarClock,
  executor: Cpu,
  gemini: Sparkles,
  webhook: Webhook,
  customer: User,
  system: Wallet,
};

/** Icon for an explorer event. */
export function eventIcon(event: AuditEventView): LucideIcon {
  if (event.display_type === "PAYMENT_CAPTURED" || event.display_type === "PROMISE_FULFILLED") {
    return CheckCircle2;
  }
  if (event.display_type === "RECOVERY_STOPPED") {
    return Ban;
  }
  if (event.display_type === "ESCALATED" || event.display_type === "PROMISE_BROKEN") {
    return AlertTriangle;
  }
  return ICONS[event.display_actor] ?? Wallet;
}

interface TimelineEventCardProps {
  event: AuditEventView;
  selected: boolean;
  onSelect: (event: AuditEventView) => void;
}

/** Compact ~70px event row. Click sends the event to the inspector. */
export function TimelineEventCard({ event, selected, onSelect }: TimelineEventCardProps) {
  const Icon = eventIcon(event);
  const tones = toneClasses(event.tone);
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(event)}
      onKeyDown={(keyboard) => {
        if (keyboard.key === "Enter" || keyboard.key === " ") {
          keyboard.preventDefault();
          onSelect(event);
        }
      }}
      aria-pressed={selected}
      data-event-key={eventKey(event)}
      className={`flex h-[70px] w-full cursor-pointer items-center gap-2.5 overflow-hidden rounded-lg border px-2.5 text-left transition-colors ${
        selected
          ? "border-info/50 bg-info-muted/40"
          : "border-border bg-surface hover:border-border-strong hover:bg-surface-hover"
      }`}
    >
      <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${tones.icon}`}>
        <Icon size={13} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-xs font-medium text-foreground">{event.summary}</span>
        <span className="mt-0.5 block truncate text-[11px] text-muted">{formatDateTime(event.timestamp)}</span>
      </span>
      <span className="flex shrink-0 flex-col items-end gap-1">
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${tones.badge}`}>
          {titleCase(event.display_actor)}
        </span>
        {event.recovery_case_id ? (
          <Link
            className="text-[10px] text-muted hover:text-info"
            to={`/recovery-queue?case=${event.recovery_case_id}`}
            onClick={(click) => click.stopPropagation()}
          >
            Open case
          </Link>
        ) : null}
      </span>
    </div>
  );
}
