import { InsightCard } from "@/components/shared/InsightCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatPaise } from "@/lib/format";
import type { AnalyticsView } from "@/types/analytics";

interface AnalyticsInsightsProps {
  model: AnalyticsView;
}

/** Four Gemini-shaped insight cards plus compliance savings. */
export function AnalyticsInsights({ model }: AnalyticsInsightsProps) {
  return (
    <section aria-label="AI insights" className="space-y-3">
      <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-4">
        {model.insights.length === 0 ? (
          <EmptyState title="No insights" description="Insights appear when metrics load." />
        ) : (
          model.insights.map((insight) => <InsightCard key={insight.title} insight={insight} />)
        )}
      </div>
      <div className="rounded-xl border border-border bg-surface px-4 py-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Compliance savings</p>
        <dl className="mt-2 grid gap-3 sm:grid-cols-3">
          <div>
            <dt className="text-[11px] text-muted">Policy stops</dt>
            <dd className="text-sm font-semibold tabular-nums">{model.compliance.stopped_cases}</dd>
          </div>
          <div>
            <dt className="text-[11px] text-muted">Suppressed revenue</dt>
            <dd className="text-sm font-semibold tabular-nums text-zinc-400">
              {formatPaise(model.compliance.suppressed_revenue)}
            </dd>
          </div>
          <div>
            <dt className="text-[11px] text-muted">Harmful retries prevented</dt>
            <dd className="text-sm font-semibold tabular-nums text-ai">
              {model.compliance.harmful_retries_prevented}
            </dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
