import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "@/components/shared/ChartCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatPaise } from "@/lib/format";
import type { StatusStackRow } from "@/types/analytics";

const TOOLTIP = {
  background: "var(--color-surface-raised)",
  border: "1px solid var(--color-border)",
  borderRadius: 8,
  fontSize: 12,
};

interface DiagnosisStackedChartProps {
  data: StatusStackRow[];
  sampleLabel: string;
}

/** Stacked status counts per diagnosis from the loaded queue. */
export function DiagnosisStackedChart({ data, sampleLabel }: DiagnosisStackedChartProps) {
  return (
    <ChartCard
      title="Recovery by diagnosis"
      description={`Status mix in the ${sampleLabel.toLowerCase()}. Stacks are case counts.`}
    >
      {data.length === 0 ? (
        <EmptyState title="No diagnosis mix" description="No queue rows in this window." />
      ) : (
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <XAxis dataKey="label" tick={{ fill: "var(--color-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fill: "var(--color-muted)", fontSize: 11 }} axisLine={false} tickLine={false} width={28} />
              <Tooltip
                formatter={(value, name) => [`${value} cases`, String(name)]}
                labelFormatter={(_, payload) => {
                  const row = payload?.[0]?.payload as StatusStackRow | undefined;
                  return row ? `${row.label} · ${formatPaise(row.revenue_paise)}` : "";
                }}
                contentStyle={TOOLTIP}
              />
              <Legend wrapperStyle={{ fontSize: 11, color: "var(--color-muted)" }} />
              <Bar dataKey="recovered" stackId="s" fill="var(--color-recovered)" name="Recovered" />
              <Bar dataKey="waiting" stackId="s" fill="var(--color-waiting)" name="Waiting" />
              <Bar dataKey="open" stackId="s" fill="var(--color-info)" name="Open" />
              <Bar dataKey="escalated" stackId="s" fill="var(--color-blocked)" name="Escalated" />
              <Bar dataKey="stopped" stackId="s" fill="#71717a" name="Stopped" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  );
}
