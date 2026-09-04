import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "@/components/shared/ChartCard";
import { formatPaise, formatPercent } from "@/lib/format";
import type { AnalyticsView } from "@/types/analytics";

interface AiBaselineChartProps {
  baseline: AnalyticsView["baseline"];
}

/** Grouped rupee comparison of RecoveryPilot vs immediate-retry baseline. */
export function AiBaselineChart({ baseline }: AiBaselineChartProps) {
  const data = [
    {
      metric: "Recovered",
      AI: baseline.ai_recovered,
      Baseline: baseline.baseline_recovered,
    },
  ];
  return (
    <ChartCard
      title="AI vs baseline"
      description={`Recovery rate ${formatPercent(baseline.ai_rate)} vs ${formatPercent(baseline.baseline_rate)} immediate retry.`}
    >
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
            <XAxis dataKey="metric" tick={{ fill: "var(--color-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis
              tickFormatter={(value: number) => formatPaise(value)}
              tick={{ fill: "var(--color-muted)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={72}
            />
            <Tooltip
              formatter={(value, name) => [formatPaise(Number(value)), String(name)]}
              contentStyle={{
                background: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey="AI" fill="var(--color-recovered)" radius={[6, 6, 0, 0]} barSize={36} />
            <Bar dataKey="Baseline" fill="#52525b" radius={[6, 6, 0, 0]} barSize={36} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartCard>
  );
}
