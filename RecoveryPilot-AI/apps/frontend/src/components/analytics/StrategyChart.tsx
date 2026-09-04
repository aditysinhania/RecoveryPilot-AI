import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "@/components/shared/ChartCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatPaise, formatPercent } from "@/lib/format";
import type { StrategyRow } from "@/types/analytics";

interface StrategyChartProps {
  data: StrategyRow[];
}

/** Recovered vs remaining cases by planner strategy. */
export function StrategyChart({ data }: StrategyChartProps) {
  return (
    <ChartCard title="Recovery by planner strategy" description="Sample outcomes for each display-mapped strategy.">
      {data.length === 0 ? (
        <EmptyState title="No strategies" description="No queue rows in this window." />
      ) : (
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="label"
                width={128}
                tick={{ fill: "var(--color-muted)", fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(value, name) => [`${value} cases`, String(name)]}
                labelFormatter={(_, payload) => {
                  const row = payload?.[0]?.payload as StrategyRow | undefined;
                  return row ? `${row.label} · ${formatPercent(row.rate)} · ${formatPaise(row.recovered_paise)}` : "";
                }}
                contentStyle={{
                  background: "var(--color-surface-raised)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="recovered" stackId="s" fill="var(--color-recovered)" name="Recovered" barSize={14} />
              <Bar dataKey="remaining" stackId="s" fill="var(--color-waiting)" name="Still open" barSize={14} radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  );
}
