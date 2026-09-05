import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartCard } from "@/components/shared/ChartCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatChartDate, formatPaise } from "@/lib/format";
import type { TrendPoint, TrendRange } from "@/types/dashboard";

interface RevenueTrendChartProps {
  data: TrendPoint[];
  range: TrendRange;
  onRangeChange: (range: TrendRange) => void;
  ranges?: TrendRange[];
  /** Hide the inner 7/30(/90) control when the parent already owns range. */
  showRangeToggle?: boolean;
}

function TooltipContent({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number; dataKey: string }>;
  label?: string;
}) {
  if (!active || !payload?.length || !label) {
    return null;
  }
  return (
    <div className="rounded-lg border border-border bg-surface-raised px-3 py-2 text-xs">
      <p className="text-muted">{formatChartDate(label)}</p>
      {payload.map((item) => (
        <p key={item.dataKey} className="text-foreground">
          {item.dataKey === "recovered_count"
            ? `Daily recoveries: ${item.value}`
            : `Recovered: ${formatPaise(item.value)}`}
        </p>
      ))}
    </div>
  );
}

/** Dual-series trend: recovered rupees (area) and daily recovery count (line). */
export function RevenueTrendChart({
  data,
  range,
  onRangeChange,
  ranges,
  showRangeToggle = true,
}: RevenueTrendChartProps) {
  return (
    <ChartCard
      title="Revenue and recoveries"
      description="Recovered rupees and daily case recoveries from the FitLife seed-42 simulation."
      action={
        showRangeToggle ? (
          <div className="flex rounded-lg border border-border p-0.5" role="group" aria-label="Trend range">
            {(ranges ?? ([7, 30] as TrendRange[])).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => onRangeChange(option)}
                className={`rounded-md px-2.5 py-1 text-xs ${
                  range === option ? "bg-surface-hover text-foreground" : "text-muted"
                }`}
                aria-pressed={range === option}
              >
                {option}d
              </button>
            ))}
          </div>
        ) : null
      }
    >
      {data.length === 0 ? (
        <EmptyState title="No trend points" description="Simulator recovered-revenue series is empty." />
      ) : (
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="recoveredFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-recovered)" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="var(--color-recovered)" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--color-border)" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={formatChartDate}
                tick={{ fill: "var(--color-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                yAxisId="paise"
                tickFormatter={(value: number) => formatPaise(value)}
                tick={{ fill: "var(--color-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={72}
              />
              <YAxis
                yAxisId="count"
                orientation="right"
                allowDecimals={false}
                tick={{ fill: "var(--color-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={28}
              />
              <Tooltip content={<TooltipContent />} />
              <Area
                yAxisId="paise"
                type="monotone"
                dataKey="recovered_paise"
                stroke="var(--color-recovered)"
                fill="url(#recoveredFill)"
                strokeWidth={2}
                name="Recovered"
              />
              <Line
                yAxisId="count"
                type="monotone"
                dataKey="recovered_count"
                stroke="var(--color-info)"
                strokeWidth={2}
                dot={false}
                name="Daily recoveries"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </ChartCard>
  );
}
