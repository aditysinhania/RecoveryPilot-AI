import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "@/components/shared/ChartCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatPaise } from "@/lib/format";
import type { PaymentMixRow } from "@/types/analytics";

interface PaymentMethodChartProps {
  data: PaymentMixRow[];
}

/** Recovered vs still-failed cases by payment rail. */
export function PaymentMethodChart({ data }: PaymentMethodChartProps) {
  return (
    <ChartCard title="Payment method outcomes" description="Queue sample grouped by the original payment rail.">
      {data.length === 0 ? (
        <EmptyState title="No methods" description="No queue rows in this window." />
      ) : (
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <XAxis dataKey="label" tick={{ fill: "var(--color-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fill: "var(--color-muted)", fontSize: 11 }} axisLine={false} tickLine={false} width={28} />
              <Tooltip
                formatter={(value, name) => [`${value} cases`, String(name)]}
                labelFormatter={(_, payload) => {
                  const row = payload?.[0]?.payload as PaymentMixRow | undefined;
                  return row ? `${row.label} · ${formatPaise(row.revenue_paise)}` : "";
                }}
                contentStyle={{
                  background: "var(--color-surface-raised)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="recovered" fill="var(--color-recovered)" name="Recovered" radius={[4, 4, 0, 0]} />
              <Bar dataKey="failed" fill="var(--color-blocked)" name="Not recovered" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  );
}
