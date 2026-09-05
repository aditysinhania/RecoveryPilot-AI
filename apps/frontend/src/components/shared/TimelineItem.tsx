import type { LucideIcon } from "lucide-react";
import {
  Ban,
  CalendarClock,
  Link2,
  ShieldAlert,
  Wallet,
  Webhook,
} from "lucide-react";
import { formatPaise, formatRelativeTime } from "@/lib/format";
import type { ActivityItem } from "@/types/dashboard";

const EVENT_META: Record<string, { label: string; icon: LucideIcon; tone: string }> = {
  ACTION_SCHEDULED: { label: "Recovery scheduled", icon: CalendarClock, tone: "text-info" },
  PAYMENT_CAPTURED: { label: "Payment captured", icon: Wallet, tone: "text-recovered" },
  PAYMENT_LINK_SENT: { label: "Payment link sent", icon: Link2, tone: "text-ai" },
  GENERATE_PAYMENT_LINK: { label: "Payment link sent", icon: Link2, tone: "text-ai" },
  PROMISE_RECORDED: { label: "Promise created", icon: CalendarClock, tone: "text-waiting" },
  RECOVERY_STOPPED: { label: "Policy blocked", icon: Ban, tone: "text-blocked" },
  POLICY_EVALUATED: { label: "Policy evaluated", icon: ShieldAlert, tone: "text-ai" },
  CASE_OPENED: { label: "Webhook received", icon: Webhook, tone: "text-info" },
  WEBHOOK_UPDATE: { label: "Webhook received", icon: Webhook, tone: "text-info" },
};

interface TimelineItemProps {
  item: ActivityItem;
}

function formatActivitySummary(summary: string): string {
  return summary.replace(/(\d+)\s*paise/gi, (_, raw: string) => formatPaise(Number(raw)));
}

/** Compact execution / audit card for the activity feed. */
export function TimelineItem({ item }: TimelineItemProps) {
  const meta = EVENT_META[item.event_type] ?? {
    label: item.summary,
    icon: ShieldAlert,
    tone: "text-muted",
  };
  const Icon = meta.icon;
  return (
    <li className="flex gap-2 rounded-lg bg-surface-raised px-2.5 py-2">
      <span
        className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-surface ${meta.tone}`}
        aria-hidden
      >
        <Icon size={14} />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium text-foreground">{meta.label}</p>
        <p className="truncate text-[11px] text-muted">{formatActivitySummary(item.summary)}</p>
        <p className="mt-0.5 text-[11px] text-muted">
          {item.actor} · <time dateTime={item.timestamp}>{formatRelativeTime(item.timestamp)}</time>
        </p>
      </div>
    </li>
  );
}
