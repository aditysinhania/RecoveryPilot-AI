import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import { cardHover, fadeUp } from "@/lib/motion";

interface OpsProbeCardProps {
  title: string;
  status: string;
  detail: string;
  icon: LucideIcon;
  meta?: string;
}

function tone(status: string): string {
  const key = status.toLowerCase();
  if (key === "ok" || key === "connected") {
    return "text-recovered";
  }
  if (key === "disabled" || key === "unconfigured" || key === "mock") {
    return "text-waiting";
  }
  return "text-blocked";
}

function pill(status: string): string {
  const key = status.toLowerCase();
  if (key === "ok" || key === "connected") {
    return "bg-recovered-muted text-recovered";
  }
  if (key === "disabled" || key === "unconfigured" || key === "mock") {
    return "bg-waiting-muted text-waiting";
  }
  return "bg-blocked-muted text-blocked";
}

/** Dependency probe tile for the operations page. */
export function OpsProbeCard({ title, status, detail, icon: Icon, meta }: OpsProbeCardProps) {
  return (
    <motion.article
      {...fadeUp}
      {...cardHover}
      className="rounded-xl border border-border bg-surface p-4 shadow-[var(--shadow-card)]"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">{title}</p>
        <Icon size={16} className={tone(status)} aria-hidden />
      </div>
      <p className={`mt-3 inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${pill(status)}`}>
        {status}
      </p>
      <p className="mt-2 text-sm text-foreground">{detail}</p>
      {meta ? <p className="mt-1 text-[11px] text-muted">{meta}</p> : null}
    </motion.article>
  );
}
