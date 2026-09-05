import { Check } from "lucide-react";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatLatency, toneClasses } from "@/lib/auditMap";
import type { CorrelationReplayView } from "@/types/audit";

interface CorrelationReplayProps {
  replay: CorrelationReplayView | null;
  loading: boolean;
}

/** Compact Diagnosis → Outcome stage strip with hop latency. */
export function CorrelationReplay({ replay, loading }: CorrelationReplayProps) {
  if (loading) {
    return <div className="h-16 animate-pulse rounded-lg bg-surface-hover" aria-hidden />;
  }
  if (!replay) {
    return (
      <EmptyState
        compact
        title="No replay loaded"
        description="Select an event or use Replay in the toolbar."
      />
    );
  }
  return (
    <div>
      <p className="text-[11px] text-muted">
        {replay.event_count} events · {formatLatency(replay.total_latency_ms)} end-to-end
      </p>
      <ol className="mt-2 flex flex-wrap gap-1.5">
        {replay.stages
          .filter((stage) => stage.key !== "payment")
          .map((stage) => {
            const filled = Boolean(stage.event);
            const tone = stage.event ? toneClasses(stage.event.tone).badge : "bg-zinc-800 text-zinc-500";
            return (
              <li key={stage.key} className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] ${tone}`}>
                {filled ? <Check size={10} aria-hidden /> : null}
                {stage.label}
                {stage.latency_ms != null ? (
                  <span className="tabular-nums opacity-80">+{formatLatency(stage.latency_ms)}</span>
                ) : null}
              </li>
            );
          })}
      </ol>
    </div>
  );
}
