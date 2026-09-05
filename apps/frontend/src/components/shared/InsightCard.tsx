import { formatRelativeTime } from "@/lib/format";
import type { DashboardInsight } from "@/types/dashboard";

const RISK: Record<string, string> = {
  LOW: "bg-recovered-muted text-recovered",
  MEDIUM: "bg-waiting-muted text-waiting",
  HIGH: "bg-blocked-muted text-blocked",
  CRITICAL: "bg-blocked-muted text-blocked",
};

interface InsightCardProps {
  insight: DashboardInsight;
}

/** One Gemini-shaped dashboard summary card. */
export function InsightCard({ insight }: InsightCardProps) {
  const risk = RISK[insight.risk_level.toUpperCase()] ?? "bg-zinc-800 text-muted";
  return (
    <article className="h-full rounded-xl border border-border bg-surface-raised p-3">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-sm font-semibold text-foreground">{insight.title}</h3>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${risk}`}>
          {insight.risk_level}
        </span>
      </div>
      <p className="mt-1.5 text-xs leading-5 text-muted">{insight.summary}</p>
      <p className="mt-2 text-xs font-medium text-ai">Next: {insight.next_action}</p>
      <div className="mt-2 flex flex-wrap gap-2 text-[10px] uppercase tracking-wide">
        <span className="rounded-full bg-ai-muted px-2 py-0.5 text-ai">
          {insight.source === "gemini" ? "Gemini" : "Fallback"}
        </span>
        {insight.cached ? (
          <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-muted">Cached</span>
        ) : null}
        <time className="text-muted" dateTime={insight.generated_at}>
          {formatRelativeTime(insight.generated_at)}
        </time>
      </div>
    </article>
  );
}
