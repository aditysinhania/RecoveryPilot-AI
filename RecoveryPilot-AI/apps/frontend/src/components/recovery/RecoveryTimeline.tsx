import { useState } from "react";
import { motion } from "framer-motion";
import {
  Ban,
  Brain,
  CalendarClock,
  Shield,
  Wallet,
  Webhook,
  type LucideIcon,
} from "lucide-react";
import { JsonHighlight } from "@/components/shared/JsonHighlight";
import { formatDateTime, titleCase } from "@/lib/format";
import type { TimelineEvent } from "@/types/recovery";

const META: Record<string, { label: string; icon: LucideIcon; tone: string }> = {
  payment_failed: { label: "Payment Failed", icon: Wallet, tone: "text-waiting bg-waiting-muted" },
  diagnosis_created: { label: "Diagnosis", icon: Brain, tone: "text-ai bg-ai-muted" },
  audit: { label: "Policy", icon: Shield, tone: "text-ai bg-ai-muted" },
  action_scheduled: { label: "Planner", icon: CalendarClock, tone: "text-info bg-info-muted" },
  action_executed: { label: "Execution Scheduled", icon: CalendarClock, tone: "text-info bg-info-muted" },
  webhook_update: { label: "Webhook Received", icon: Webhook, tone: "text-info bg-info-muted" },
  recovered: { label: "Payment Captured", icon: Wallet, tone: "text-recovered bg-recovered-muted" },
  stopped: { label: "Stopped", icon: Ban, tone: "text-zinc-400 bg-zinc-800" },
};

function metaFor(event: TimelineEvent): { label: string; icon: LucideIcon; tone: string } {
  const summary = String(event.summary).toLowerCase();
  if (event.event_type === "webhook_update" && (summary.includes("captured") || summary.includes("paid"))) {
    return META.recovered;
  }
  if (
    (event.event_type === "action_executed" || event.event_type === "webhook_update") &&
    (summary.includes("stop") || summary.includes("stopped"))
  ) {
    return META.stopped;
  }
  return META[event.event_type] ?? {
    label: titleCase(event.event_type),
    icon: Shield,
    tone: "text-muted bg-zinc-800",
  };
}

interface RecoveryTimelineProps {
  events: TimelineEvent[];
}

/** Vertical recovery journey. Each event expands to pretty-printed details. */
export function RecoveryTimeline({ events }: RecoveryTimelineProps) {
  const [openId, setOpenId] = useState<string | null>(null);
  const ordered = [...events].sort((a, b) => Date.parse(a.occurred_at) - Date.parse(b.occurred_at));
  return (
    <section className="rounded-xl border border-border bg-surface-raised p-4" aria-labelledby="timeline-heading">
      <h3 id="timeline-heading" className="text-[11px] font-semibold uppercase tracking-wide text-muted">
        Recovery Timeline
      </h3>
      {ordered.length === 0 ? (
        <p className="mt-3 text-xs text-muted">No timeline events for this case.</p>
      ) : (
        <ol className="mt-3 space-y-0">
          {ordered.map((event, index) => {
            const meta = metaFor(event);
            const Icon = meta.icon;
            const id = `${event.event_type}-${event.occurred_at}-${index}`;
            const expanded = openId === id;
            return (
              <motion.li
                key={id}
                initial={{ opacity: 0, x: 8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: Math.min(index * 0.04, 0.24) }}
                className="relative flex gap-3 pb-4 last:pb-0"
              >
                {index < ordered.length - 1 ? (
                  <span className="absolute left-[15px] top-8 h-[calc(100%-12px)] w-px bg-border" aria-hidden />
                ) : null}
                <span
                  className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${meta.tone}`}
                >
                  <Icon size={14} aria-hidden />
                </span>
                <button
                  type="button"
                  className="min-w-0 flex-1 rounded-lg bg-surface px-3 py-2 text-left hover:bg-surface-hover"
                  onClick={() => setOpenId(expanded ? null : id)}
                  aria-expanded={expanded}
                >
                  <p className="text-xs font-medium text-foreground">{meta.label}</p>
                  <p className="mt-0.5 text-[11px] text-muted">{event.summary}</p>
                  <p className="mt-0.5 text-[11px] text-zinc-500">
                    {formatDateTime(event.occurred_at)} · {event.source}
                  </p>
                  {expanded ? <JsonHighlight value={event.details} /> : null}
                </button>
              </motion.li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
