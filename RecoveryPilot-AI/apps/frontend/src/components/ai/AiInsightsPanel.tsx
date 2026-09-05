import { ChevronLeft, ChevronRight, Sparkles } from "lucide-react";
import { useRef } from "react";
import { InsightCard } from "@/components/shared/InsightCard";
import { EmptyState } from "@/components/shared/EmptyState";
import type { DashboardInsight } from "@/types/dashboard";

interface AiInsightsPanelProps {
  insights: DashboardInsight[];
}

/** Horizontal insight carousel. Max three Gemini-shaped cards. */
export function AiInsightsPanel({ insights }: AiInsightsPanelProps) {
  const shown = insights.slice(0, 3);
  const scrollerRef = useRef<HTMLDivElement>(null);

  const scrollByCard = (direction: -1 | 1): void => {
    const root = scrollerRef.current;
    if (!root) {
      return;
    }
    const card = root.querySelector<HTMLElement>("[data-insight-card]");
    const delta = (card?.offsetWidth ?? 280) + 12;
    root.scrollBy({ left: direction * delta, behavior: "smooth" });
  };

  return (
    <section aria-label="AI insights" data-tour="insights" className="rounded-xl border border-ai/30 bg-surface px-4 py-3 shadow-[var(--shadow-card)]">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-ai">
          <Sparkles size={16} aria-hidden />
          <h2 className="text-sm font-semibold text-foreground">AI insights</h2>
        </div>
        {shown.length > 1 ? (
          <div className="flex gap-1">
            <button
              type="button"
              className="rounded-lg p-1 text-muted hover:bg-surface-hover hover:text-foreground"
              aria-label="Previous insight"
              onClick={() => scrollByCard(-1)}
            >
              <ChevronLeft size={16} />
            </button>
            <button
              type="button"
              className="rounded-lg p-1 text-muted hover:bg-surface-hover hover:text-foreground"
              aria-label="Next insight"
              onClick={() => scrollByCard(1)}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        ) : null}
      </div>
      {shown.length === 0 ? (
        <EmptyState title="No insights yet" description="Dashboard summaries appear when metrics load." />
      ) : (
        <div
          ref={scrollerRef}
          className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-1 [scrollbar-width:thin]"
          role="region"
          aria-roledescription="carousel"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === "ArrowRight") {
              event.preventDefault();
              scrollByCard(1);
            }
            if (event.key === "ArrowLeft") {
              event.preventDefault();
              scrollByCard(-1);
            }
          }}
        >
          {shown.map((insight) => (
            <div
              key={insight.title}
              data-insight-card
              className="min-w-[min(100%,280px)] max-w-sm shrink-0 snap-start lg:min-w-[calc((100%-24px)/3)]"
            >
              <InsightCard insight={insight} />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
