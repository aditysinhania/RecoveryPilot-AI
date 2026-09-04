import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "@/components/shared/ChartCard";
import { formatChartDate, formatPaise } from "@/lib/format";
import type { CalendarBucket, FestivalImpactRow } from "@/types/analytics";

interface CalendarImpactChartProps {
  calendar: CalendarBucket[];
  festivals: FestivalImpactRow[];
}

/** Salary-cycle buckets from the daily recovered series, plus festival markers. */
export function CalendarImpactChart({ calendar, festivals }: CalendarImpactChartProps) {
  return (
    <ChartCard
      title="Salary cycle and festivals"
      description="Recovered rupees by calendar-day bucket from the seed-42 trend. FitLife festival bias is off."
    >
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={calendar} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="label" tick={{ fill: "var(--color-muted)", fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis
              tickFormatter={(value: number) => formatPaise(value)}
              tick={{ fill: "var(--color-muted)", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={72}
            />
            <Tooltip
              formatter={(value, _name, item) => {
                const row = (item as { payload?: CalendarBucket }).payload;
                return [`${formatPaise(Number(value))} · ${row?.recovered_count ?? 0} captures`, "Recovered"];
              }}
              contentStyle={{
                background: "var(--color-surface-raised)",
                border: "1px solid var(--color-border)",
                borderRadius: 8,
                fontSize: 12,
              }}
            />
            <Bar dataKey="recovered_paise" fill="var(--color-waiting)" radius={[6, 6, 0, 0]} barSize={36} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ul className="mt-3 space-y-1.5 text-[11px]">
        {festivals.length === 0 ? (
          <li className="text-muted">No festival dates fall in this window.</li>
        ) : (
          festivals.map((fest) => (
            <li key={fest.date} className="flex flex-wrap items-baseline justify-between gap-2 text-muted">
              <span>
                <span className="font-medium text-foreground">{fest.name}</span>
                {" · "}
                {formatChartDate(fest.date)}
                {" · "}
                {fest.applied ? "bias on" : "not applied"}
              </span>
              <span className="tabular-nums">
                {formatPaise(fest.recovered_paise)} vs {formatPaise(fest.typical_paise)} typical
              </span>
            </li>
          ))
        )}
      </ul>
    </ChartCard>
  );
}
