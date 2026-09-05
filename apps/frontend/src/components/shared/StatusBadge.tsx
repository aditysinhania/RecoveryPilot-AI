import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Ban,
  CalendarClock,
  CheckCircle2,
  CircleDashed,
  Clock3,
  HeartHandshake,
  Link2,
  RotateCw,
  Send,
  Shield,
  ShieldAlert,
  ShieldOff,
} from "lucide-react";
import { titleCase } from "@/lib/format";

const STATUS_META: Record<string, { label: string; cls: string; icon?: LucideIcon }> = {
  RECOVERED: { label: "Recovered", cls: "bg-recovered-muted text-recovered", icon: CheckCircle2 },
  WAITING_RETRY: { label: "Waiting", cls: "bg-waiting-muted text-waiting", icon: Clock3 },
  WAITING_PROMISE: { label: "Promise Active", cls: "bg-ai-muted text-ai", icon: HeartHandshake },
  OPEN: { label: "Open", cls: "bg-waiting-muted text-waiting", icon: Clock3 },
  DIAGNOSED: { label: "Diagnosed", cls: "bg-info-muted text-info", icon: CircleDashed },
  SCHEDULED: { label: "Scheduled", cls: "bg-info-muted text-info", icon: CalendarClock },
  STOPPED: { label: "Stopped", cls: "bg-zinc-800 text-zinc-400", icon: Ban },
  CLOSED: { label: "Closed", cls: "bg-zinc-800 text-zinc-400", icon: Ban },
  ESCALATED: { label: "Escalated", cls: "bg-blocked-muted text-blocked", icon: AlertTriangle },
  ALLOW: { label: "Allow", cls: "bg-recovered-muted text-recovered", icon: Shield },
  WAIT: { label: "Wait", cls: "bg-waiting-muted text-waiting", icon: Clock3 },
  DENY: { label: "Deny", cls: "bg-zinc-800 text-zinc-400", icon: ShieldOff },
  ESCALATE: { label: "Escalate", cls: "bg-blocked-muted text-blocked", icon: ShieldAlert },
  STOP: { label: "Stop", cls: "bg-zinc-800 text-zinc-400", icon: Ban },
  EXECUTED: { label: "Executed", cls: "bg-recovered-muted text-recovered", icon: CheckCircle2 },
  SKIPPED: { label: "Skipped", cls: "bg-zinc-800 text-zinc-400", icon: Ban },
  FAILED: { label: "Failed", cls: "bg-blocked-muted text-blocked", icon: AlertTriangle },
  PENDING: { label: "Pending", cls: "bg-waiting-muted text-waiting", icon: Clock3 },
  SENT: { label: "Sent", cls: "bg-info-muted text-info", icon: Send },
  SUCCESS: { label: "Success", cls: "bg-recovered-muted text-recovered", icon: CheckCircle2 },
  EXPIRED: { label: "Expired", cls: "bg-zinc-800 text-zinc-400", icon: Ban },
  CANCELLED: { label: "Cancelled", cls: "bg-zinc-800 text-zinc-400", icon: Ban },
  RETRYING: { label: "Retrying", cls: "bg-waiting-muted text-waiting", icon: RotateCw },
  "Link Sent": { label: "Link Sent", cls: "bg-info-muted text-info", icon: Link2 },
  Delivered: { label: "Delivered", cls: "bg-recovered-muted text-recovered", icon: CheckCircle2 },
  Scheduled: { label: "Scheduled", cls: "bg-info-muted text-info", icon: CalendarClock },
  Retrying: { label: "Retrying", cls: "bg-waiting-muted text-waiting", icon: RotateCw },
  Failed: { label: "Failed", cls: "bg-blocked-muted text-blocked", icon: AlertTriangle },
  PASS: { label: "Pass", cls: "bg-recovered-muted text-recovered", icon: CheckCircle2 },
  FAIL: { label: "Fail", cls: "bg-blocked-muted text-blocked", icon: AlertTriangle },
};

interface StatusBadgeProps {
  status: string;
}

/** Colored recovery / policy / execution status pill with an icon. */
export function StatusBadge({ status }: StatusBadgeProps) {
  const meta = STATUS_META[status] ?? STATUS_META[status.toUpperCase()];
  const cls = meta?.cls ?? "bg-zinc-800 text-muted";
  const label = meta?.label ?? titleCase(status);
  const Icon = meta?.icon;
  return (
    <span
      className={`inline-flex max-w-full min-w-0 items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ${cls}`}
      title={label}
    >
      {Icon ? <Icon size={11} strokeWidth={2.4} aria-hidden className="shrink-0" /> : null}
      <span className="truncate">{label}</span>
    </span>
  );
}
