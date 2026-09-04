import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "@/components/shared/ChartCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatPaise, formatPercent } from "@/lib/format";
import type { MixRow } from "@/types/analytics";

interface MixBarChartProps {
  title: string;
  description: string;
  data: MixRow[];
}

/** Horizontal recovered vs remaining mix (segment or plan). */
export function MixBarChart({ title, description, data }: MixBarChartProps) {
  return (
    <ChartCard title={title} description={description}>
      {data.length === 0 ? (
        <EmptyState title="No mix" description="No queue rows in this window." />
      ) : (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 0, right: 12, left: 4, bottom: 0 }}>
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="label"
                width={88}
                tick={{ fill: "var(--color-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(value, name) => [
                  name === "recovered_paise" ? formatPaise(Number(value)) : String(value),
                  name === "recovered_paise" ? "Recovered" : "Cases",
                ]}
                labelFormatter={(_, payload) => {
                  const row = payload?.[0]?.payload as MixRow | undefined;
                  return row ? `${row.label} · ${formatPercent(row.count ? row.recovered / row.count : 0)}` : "";
                }}
                contentStyle={{
                  background: "var(--color-surface-raised)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Bar dataKey="recovered_paise" fill="var(--color-recovered)" name="recovered_paise" barSize={14} radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  );
}
