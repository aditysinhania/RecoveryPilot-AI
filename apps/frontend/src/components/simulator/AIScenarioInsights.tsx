import { InsightCard } from "@/components/shared/InsightCard";
import { SectionHeader } from "@/components/shared/SectionHeader";
import type { DashboardInsight } from "@/types/dashboard";

interface AIScenarioInsightsProps {
  insights: DashboardInsight[];
}

/** Gemini-shaped recommendation cards. Always fallback in this phase. */
export function AIScenarioInsights({ insights }: AIScenarioInsightsProps) {
  return (
    <section>
      <SectionHeader
        title="AI decision summary"
        description="Fallback copy in the Gemini dashboard shape. No model call in this lab."
      />
      <div className="grid gap-3 md:grid-cols-2">
        {insights.map((insight) => (
          <InsightCard key={insight.title} insight={insight} />
        ))}
      </div>
    </section>
  );
}
