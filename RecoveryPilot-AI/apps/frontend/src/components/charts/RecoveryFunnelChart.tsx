import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "@/components/shared/ChartCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatCompactPaise, formatPaise } from "@/lib/format";
import type { FunnelStage } from "@/types/dashboard";

interface RecoveryFunnelChartProps {
  data: FunnelStage[];
}

/** Horizontal recovery funnel: at risk → recovered. */
export function RecoveryFunnelChart({ data }: RecoveryFunnelChartProps) {
  return (
    <ChartCard title="Recovery funnel" description="Case counts and rupees at each engine stage.">
      {data.length === 0 ? (
        <EmptyState title="No funnel data" description="Recovery stages have not been computed." />
      ) : (
        <div className="h-44">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="stage"
                width={120}
                tick={{ fill: "var(--color-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(value, _name, item) => {
                  const stage = (item as { payload?: FunnelStage }).payload;
                  return [`${value} cases · ${formatPaise(stage?.revenue_paise ?? 0)}`, "Stage"];
                }}
                contentStyle={{
                  background: "var(--color-surface-raised)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Bar dataKey="count" fill="var(--color-info)" radius={[0, 6, 6, 0]} barSize={18} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      {data.length > 0 ? (
        <dl className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-muted sm:grid-cols-5">
          {data.map((stage) => (
            <div key={stage.stage}>
              <dt>{stage.stage}</dt>
              <dd className="font-medium text-foreground">{formatCompactPaise(stage.revenue_paise)}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </ChartCard>
  );
}
