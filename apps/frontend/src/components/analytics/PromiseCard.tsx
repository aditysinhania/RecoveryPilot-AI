import { HeartHandshake } from "lucide-react";
import { ChartCard } from "@/components/shared/ChartCard";
import { formatPercent } from "@/lib/format";
import type { PromiseStats } from "@/types/analytics";

interface PromiseCardProps {
  stats: PromiseStats;
}

/** Promise-to-pay success from honour-promise queue rows plus cohort active count. */
export function PromiseCard({ stats }: PromiseCardProps) {
  const pct = Math.round(stats.rate * 100);
  return (
    <ChartCard
      title="Promise-to-pay"
      description="Honour-promise rows in the loaded queue, plus cohort promises still active."
    >
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-ai-muted text-ai" aria-hidden>
          <HeartHandshake size={16} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-2xl font-semibold tabular-nums text-ai">{formatPercent(stats.rate, 0)}</p>
          <p className="text-xs text-muted">
            {stats.recovered} recovered · {stats.active} still active
            {stats.sample_size ? ` · ${stats.sample_size} sample cases` : ""}
          </p>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-zinc-800" aria-hidden>
            <div className="h-full rounded-full bg-ai" style={{ width: `${pct}%` }} />
          </div>
        </div>
      </div>
    </ChartCard>
  );
}
