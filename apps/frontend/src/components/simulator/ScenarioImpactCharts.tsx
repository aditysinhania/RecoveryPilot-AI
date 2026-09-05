import { Bar, BarChart, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
} from "recharts";
import { DiagnosisStackedChart } from "@/components/analytics/DiagnosisStackedChart";
import { MixBarChart } from "@/components/analytics/MixBarChart";
import { PaymentMethodChart } from "@/components/analytics/PaymentMethodChart";
import { StrategyChart } from "@/components/analytics/StrategyChart";
import { ChartCard } from "@/components/shared/ChartCard";
import { formatChartDate, formatPaise } from "@/lib/format";
import type { ScenarioResult } from "@/types/simulatorLab";

interface ScenarioImpactChartsProps {
  current: ScenarioResult;
  seed42: ScenarioResult;
}

/** Scenario mix charts plus AI vs baseline funnel and before/after timeline. */
export function ScenarioImpactCharts({ current, seed42 }: ScenarioImpactChartsProps) {
  const funnel = [
    {
      stage: "At Risk",
      AI: current.funnel_ai[0]?.count ?? current.cases,
      Baseline: current.funnel_baseline[0]?.count ?? current.cases,
    },
    {
      stage: "Diagnosed",
      AI: current.funnel_ai[1]?.count ?? current.cases,
      Baseline: current.funnel_baseline[1]?.count ?? current.cases,
    },
    {
      stage: "Planned",
      AI: current.funnel_ai[3]?.count ?? current.funnel_ai[2]?.count ?? 0,
      Baseline: current.funnel_baseline[2]?.count ?? current.cases,
    },
    {
      stage: "Recovered",
      AI: current.funnel_ai[current.funnel_ai.length - 1]?.count ?? 0,
      Baseline: current.funnel_baseline[current.funnel_baseline.length - 1]?.count ?? 0,
    },
  ];
  const timeline = current.trend.map((point) => {
    const before = seed42.trend.find((item) => item.date === point.date);
    return {
      date: point.date,
      after: point.recovered_paise,
      before: before?.recovered_paise ?? 0,
      baseline: point.baseline_paise,
    };
  });

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <ChartCard title="Recovery funnel comparison" description="Case counts: RecoveryPilot versus the selected baseline.">
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={funnel} layout="vertical" margin={{ top: 0, right: 12, left: 8, bottom: 0 }}>
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="stage"
                width={108}
                tick={{ fill: "var(--color-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--color-surface-raised)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="AI" fill="var(--color-recovered)" barSize={10} radius={[0, 6, 6, 0]} />
              <Bar dataKey="Baseline" fill="#52525b" barSize={10} radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
      <DiagnosisStackedChart data={current.diagnosis} sampleLabel="simulated mix" />
      <StrategyChart data={current.strategies} />
      <MixBarChart
        title="Customer segment recovery"
        description="Recovered rupees weighted by the selected merchant persona mix."
        data={current.segments}
      />
      <PaymentMethodChart data={current.methods} />
      <ChartCard
        title="Revenue timeline before vs after"
        description="Seed-42 recovered rupees versus this scenario. Grey line is the scenario baseline."
      >
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={timeline} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="labAfterFill" x1="0" y1="0" x2="0" y2="1">
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
                tickFormatter={(value: number) => formatPaise(value)}
                tick={{ fill: "var(--color-muted)", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={72}
              />
              <Tooltip
                formatter={(value, name) => [formatPaise(Number(value)), String(name)]}
                labelFormatter={(label) => formatChartDate(String(label))}
                contentStyle={{
                  background: "var(--color-surface-raised)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area
                type="monotone"
                dataKey="after"
                name="This scenario"
                stroke="var(--color-recovered)"
                fill="url(#labAfterFill)"
                strokeWidth={2}
              />
              <Line type="monotone" dataKey="before" name="Seed 42" stroke="var(--color-ai)" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="baseline" name="Baseline" stroke="#71717a" strokeWidth={1.5} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </ChartCard>
    </div>
  );
}
