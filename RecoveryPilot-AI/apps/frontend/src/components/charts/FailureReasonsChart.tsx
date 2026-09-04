import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { ChartCard } from "@/components/shared/ChartCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatPaise } from "@/lib/format";
import type { FailureReasonSlice } from "@/types/dashboard";

const SLICE_COLOR: Record<string, string> = {
  INSUFFICIENT_FUNDS: "var(--color-waiting)",
  CARD_EXPIRED: "var(--color-info)",
  UPI_FAILURE: "var(--color-ai)",
  MANDATE_REVOKED: "var(--color-blocked)",
  BANK_TIMEOUT: "var(--color-recovered)",
  OTHER: "var(--color-muted)",
};

interface FailureReasonsChartProps {
  data: FailureReasonSlice[];
}

/** Donut of diagnosed failure reasons from the FitLife ledger. */
export function FailureReasonsChart({ data }: FailureReasonsChartProps) {
  const total = data.reduce((sum, item) => sum + item.count, 0);
  return (
    <ChartCard title="Failure reasons" description="Original failed payments in the seed-42 cohort.">
      {total === 0 ? (
        <EmptyState title="No failures" description="Failure distribution is empty." />
      ) : (
        <div className="grid gap-4 md:grid-cols-[180px_1fr]">
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  dataKey="count"
                  nameKey="label"
                  innerRadius={48}
                  outerRadius={72}
                  paddingAngle={2}
                >
                  {data.map((slice) => (
                    <Cell key={slice.key} fill={SLICE_COLOR[slice.key] ?? "var(--color-muted)"} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value, _name, item) => {
                    const slice = (item as { payload?: FailureReasonSlice }).payload;
                    return [`${value} · ${formatPaise(slice?.revenue_paise ?? 0)}`, slice?.label ?? ""];
                  }}
                  contentStyle={{
                    background: "var(--color-surface-raised)",
                    border: "1px solid var(--color-border)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <ul className="space-y-2 self-center">
            {data.map((slice) => (
              <li key={slice.key} className="flex items-center justify-between gap-3 text-xs">
                <span className="flex items-center gap-2 text-muted">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: SLICE_COLOR[slice.key] }}
                    aria-hidden
                  />
                  {slice.label}
                </span>
                <span className="font-medium text-foreground">{slice.count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </ChartCard>
  );
}
