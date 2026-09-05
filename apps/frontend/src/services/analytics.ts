import { SNAPSHOT } from "@/services/dashboard";
import { formatPaise, formatPercent, isoDate, titleCase } from "@/lib/format";
import { plannerStrategyFor, recoveryProbability } from "@/lib/recoveryMap";
import type { AnalyticsRange, AnalyticsView, MixRow, StatusStackRow, StrategyRow } from "@/types/analytics";
import type { DashboardInsight, DashboardView, FitlifeSnapshot, TrendPoint } from "@/types/dashboard";
import type { QueueRow } from "@/types/recovery";

const FESTIVALS: { date: string; name: string; effect: string }[] = [
  { date: "2026-06-17", name: "Bakrid / Eid al-Adha", effect: "UPI congestion + festive spend" },
  { date: "2026-06-26", name: "Muharram (Ashura)", effect: "Lower banking hours in some states" },
  { date: "2026-06-27", name: "Rath Yatra", effect: "Regional UPI spike (east / coastal)" },
  { date: "2026-07-29", name: "Guru Purnima", effect: "Gift UPI volume" },
  { date: "2026-08-15", name: "Independence Day", effect: "Bank holiday + UPI timeouts" },
  { date: "2026-08-26", name: "Onam (Thiruvonam)", effect: "Kerala / south UPI spike" },
  { date: "2026-08-28", name: "Raksha Bandhan", effect: "Gift transfers, card + UPI load" },
  { date: "2026-09-04", name: "Janmashtami", effect: "Evening UPI congestion" },
];

const OPEN_STATUSES = new Set(["OPEN", "DIAGNOSED", "WAITING_RETRY", "WAITING_PROMISE"]);

function clampSummary(text: string): string {
  if (text.length <= 160) {
    return text;
  }
  return `${text.slice(0, 157)}...`;
}

function cutoffIso(asOf: string, range: AnalyticsRange): string {
  const end = Date.parse(asOf);
  if (Number.isNaN(end)) {
    return asOf.slice(0, 10);
  }
  return new Date(end - range * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

function inRange(iso: string, start: string, end: string): boolean {
  const day = isoDate(iso) || iso.slice(0, 10);
  return day >= start && day <= end;
}

function statusBucket(status: string): keyof Pick<StatusStackRow, "recovered" | "waiting" | "escalated" | "stopped" | "open"> {
  if (status === "RECOVERED") {
    return "recovered";
  }
  if (status === "WAITING_RETRY" || status === "WAITING_PROMISE") {
    return "waiting";
  }
  if (status === "ESCALATED") {
    return "escalated";
  }
  if (status === "STOPPED" || status === "CLOSED") {
    return "stopped";
  }
  return "open";
}

function emptyStack(key: string, label: string): StatusStackRow {
  return { key, label, recovered: 0, waiting: 0, escalated: 0, stopped: 0, open: 0, revenue_paise: 0 };
}

function diagnosisLabel(key: string): string {
  const slice = SNAPSHOT.failure_reasons.find((item) => item.key === key);
  if (slice) {
    return slice.label;
  }
  return titleCase(key);
}

function addMix(map: Map<string, MixRow>, key: string, label: string, row: QueueRow): void {
  const current = map.get(key) ?? {
    key,
    label,
    count: 0,
    recovered: 0,
    revenue_paise: 0,
    recovered_paise: 0,
  };
  current.count += 1;
  current.revenue_paise += row.amount;
  if (row.recovery_status === "RECOVERED") {
    current.recovered += 1;
    current.recovered_paise += row.amount;
  }
  map.set(key, current);
}

function recoveryRate(recovered: number, total: number): number {
  if (total <= 0) {
    return 0;
  }
  return recovered / total;
}

function buildInsights(view: AnalyticsView, generatedAt: string): DashboardInsight[] {
  const topLoss = view.loss_leaders[0];
  const best = [...view.strategies].sort((a, b) => b.rate - a.rate || b.recovered_paise - a.recovered_paise)[0];
  return [
    {
      title: topLoss ? `${topLoss.label} drives most at-risk rupees` : "Diagnosis mix is balanced",
      summary: clampSummary(
        topLoss
          ? `${topLoss.label} is ${topLoss.count} failed invoices (${formatPaise(topLoss.revenue_paise)}). Payday waits beat immediate retries on NSF.`
          : "No diagnosis slice is available in this range.",
      ),
      risk_level: "HIGH",
      next_action: "Keep NSF on payday wait; do not blast retries.",
      source: "fallback",
      cached: true,
      generated_at: generatedAt,
    },
    {
      title: best ? `${best.label} is the strongest planner move` : "Planner mix is thin",
      summary: clampSummary(
        best
          ? `${best.label} recovered ${best.recovered} of ${best.recovered + best.remaining} sample cases (${formatPercent(best.rate)}).`
          : "Not enough queue rows to rank planner strategies.",
      ),
      risk_level: "MEDIUM",
      next_action: "Protect high-performing strategies in policy.",
      source: "fallback",
      cached: true,
      generated_at: generatedAt,
    },
    {
      title: "Stopping rules save compliance load",
      summary: clampSummary(
        `Policy stops closed ${view.compliance.stopped_cases} cases and prevented ${view.compliance.harmful_retries_prevented} harmful retries. Suppressed revenue ${formatPaise(view.compliance.suppressed_revenue)}.`,
      ),
      risk_level: "LOW",
      next_action: "Do not chase revoked mandates, disputes, or already-paid invoices.",
      source: "fallback",
      cached: true,
      generated_at: generatedAt,
    },
    {
      title: "AI lift versus immediate-retry baseline",
      summary: clampSummary(
        `RecoveryPilot recovered ${formatPaise(view.baseline.ai_recovered)} (${formatPercent(view.baseline.ai_rate)}) versus ${formatPaise(view.baseline.baseline_recovered)} baseline (${formatPercent(view.baseline.baseline_rate)}).`,
      ),
      risk_level: "MEDIUM",
      next_action: "Keep bounded retries; do not revert to blast SMS.",
      source: "fallback",
      cached: true,
      generated_at: generatedAt,
    },
  ];
}

/** Client-side analytics view. Display maps only — engines are not called. */
export function assembleAnalytics(
  dashboard: DashboardView,
  queue: QueueRow[],
  fullTrend: TrendPoint[],
  range: AnalyticsRange,
  snapshot: FitlifeSnapshot = SNAPSHOT,
): AnalyticsView {
  const asOf = snapshot.as_of;
  const start = cutoffIso(asOf, range);
  const end = asOf.slice(0, 10);
  const rows = queue.filter((row) => inRange(row.failed_at, start, end));
  const trend = fullTrend.filter((point) => point.date >= start && point.date <= end);

  const diagnosis = new Map<string, StatusStackRow>();
  const strategies = new Map<string, StrategyRow>();
  const segments = new Map<string, MixRow>();
  const plans = new Map<string, MixRow>();
  const methods = new Map<string, { key: string; label: string; recovered: number; failed: number; revenue_paise: number }>();

  for (const row of rows) {
    const reason = row.diagnosed_reason ?? row.failure_reason ?? "UNKNOWN";
    const mapped = reason === "CUSTOMER_CANCELLED" || reason === "ALREADY_PAID" || reason === "DISPUTE" || reason === "UNKNOWN"
      ? "OTHER"
      : reason;
    const stack = diagnosis.get(mapped) ?? emptyStack(mapped, diagnosisLabel(mapped));
    stack[statusBucket(row.recovery_status)] += 1;
    stack.revenue_paise += row.amount;
    diagnosis.set(mapped, stack);

    const strategyKey = row.planner_strategy || plannerStrategyFor(reason, row.recovery_status);
    const strategy = strategies.get(strategyKey) ?? {
      key: strategyKey,
      label: titleCase(strategyKey),
      recovered: 0,
      remaining: 0,
      recovered_paise: 0,
      rate: 0,
    };
    if (row.recovery_status === "RECOVERED") {
      strategy.recovered += 1;
      strategy.recovered_paise += row.amount;
    } else {
      strategy.remaining += 1;
    }
    strategies.set(strategyKey, strategy);

    addMix(segments, row.customer_segment, titleCase(row.customer_segment), row);
    addMix(plans, row.plan_name, row.plan_name, row);

    const methodKey = (row.payment_method ?? "UNKNOWN").toUpperCase();
    const method = methods.get(methodKey) ?? {
      key: methodKey,
      label: titleCase(methodKey),
      recovered: 0,
      failed: 0,
      revenue_paise: 0,
    };
    method.revenue_paise += row.amount;
    if (row.recovery_status === "RECOVERED") {
      method.recovered += 1;
    } else {
      method.failed += 1;
    }
    methods.set(methodKey, method);
  }

  const strategyRows = [...strategies.values()]
    .map((item) => ({
      ...item,
      rate: recoveryRate(item.recovered, item.recovered + item.remaining),
    }))
    .sort((a, b) => b.recovered_paise - a.recovered_paise);

  const promiseRows = rows.filter(
    (row) => row.recovery_status === "WAITING_PROMISE" || row.planner_strategy === "HONOUR_PROMISE_TO_PAY",
  );
  const promiseRecovered = promiseRows.filter((row) => row.recovery_status === "RECOVERED").length;
  const promiseActive = promiseRows.filter((row) => row.recovery_status === "WAITING_PROMISE").length;

  const opportunities = rows
    .filter((row) => OPEN_STATUSES.has(row.recovery_status))
    .map((row) => {
      const reason = row.diagnosed_reason ?? row.failure_reason ?? "UNKNOWN";
      const probability = recoveryProbability(row.customer_segment, reason, row.recovery_status);
      return {
        recovery_case_id: row.recovery_case_id,
        customer_name: row.customer_name,
        plan_name: row.plan_name,
        diagnosis: titleCase(reason),
        strategy: titleCase(row.planner_strategy),
        amount: row.amount,
        expected_paise: Math.round(row.amount * probability),
        recovery_status: row.recovery_status,
      };
    })
    .sort((a, b) => b.expected_paise - a.expected_paise)
    .slice(0, 8);

  const bankSlice = snapshot.failure_reasons.find((item) => item.key === "BANK_TIMEOUT");
  const failureTotal = snapshot.failure_reasons.reduce((sum, item) => sum + item.count, 0);
  const bankRows = rows.filter((row) => (row.diagnosed_reason ?? row.failure_reason) === "BANK_TIMEOUT");
  const otherRows = rows.filter((row) => (row.diagnosed_reason ?? row.failure_reason) !== "BANK_TIMEOUT");

  const calendarMap = new Map<string, { key: string; label: string; recovered_paise: number; recovered_count: number }>([
    ["payday", { key: "payday", label: "Days 1–5 (salary credit)", recovered_paise: 0, recovered_count: 0 }],
    ["mid", { key: "mid", label: "Days 6–24", recovered_paise: 0, recovered_count: 0 }],
    ["squeeze", { key: "squeeze", label: "Days 25–31 (pre-payday)", recovered_paise: 0, recovered_count: 0 }],
  ]);
  for (const point of trend) {
    const day = Number(point.date.slice(8, 10));
    const bucket = day <= 5 ? "payday" : day >= 25 ? "squeeze" : "mid";
    const current = calendarMap.get(bucket);
    if (!current) {
      continue;
    }
    current.recovered_paise += point.recovered_paise;
    current.recovered_count += point.recovered_count;
  }

  const typical =
    trend.length > 0 ? trend.reduce((sum, point) => sum + point.recovered_paise, 0) / trend.length : 0;
  const festivals = FESTIVALS.filter((fest) => fest.date >= start && fest.date <= end).map((fest) => {
    const point = fullTrend.find((item) => item.date === fest.date);
    return {
      date: fest.date,
      name: fest.name,
      effect: fest.effect,
      applied: false,
      recovered_paise: point?.recovered_paise ?? 0,
      typical_paise: Math.round(typical),
    };
  });

  const lossLeaders = [...snapshot.failure_reasons].sort((a, b) => b.revenue_paise - a.revenue_paise);

  const model: AnalyticsView = {
    range,
    sample_size: rows.length,
    sample_label: rows.length >= 20 ? "Loaded recovery queue" : "FitLife queue catalog",
    kpis: {
      revenue_at_risk: dashboard.kpis.revenue_at_risk,
      recovered_revenue: dashboard.kpis.recovered_by_ai,
      recovery_rate: dashboard.kpis.recovery_rate,
      ai_lift: dashboard.kpis.ai_lift,
      pending_recovery_value: dashboard.kpis.pending_recovery_value,
      harmful_retries_prevented: dashboard.lift.harmful_retries_prevented,
    },
    diagnosis_stack: [...diagnosis.values()].sort((a, b) => b.revenue_paise - a.revenue_paise),
    strategies: strategyRows,
    baseline: {
      ai_recovered: dashboard.lift.recovered_by_ai,
      baseline_recovered: dashboard.lift.recovered_by_baseline,
      ai_rate: dashboard.lift.ai_rate,
      baseline_rate: dashboard.lift.baseline_rate,
    },
    funnel: dashboard.funnel,
    segments: [...segments.values()].sort((a, b) => b.revenue_paise - a.revenue_paise),
    plans: [...plans.values()].sort((a, b) => b.revenue_paise - a.revenue_paise),
    promises: {
      active: promiseActive || dashboard.health.promise_active,
      recovered: promiseRecovered,
      rate: recoveryRate(promiseRecovered, promiseRecovered + (promiseActive || dashboard.health.promise_active)),
      sample_size: promiseRows.length,
    },
    opportunities,
    payment_methods: [...methods.values()].sort((a, b) => b.revenue_paise - a.revenue_paise),
    trend,
    bank: {
      cases: bankSlice?.count ?? bankRows.length,
      revenue_paise: bankSlice?.revenue_paise ?? bankRows.reduce((sum, row) => sum + row.amount, 0),
      share: failureTotal > 0 ? (bankSlice?.count ?? 0) / failureTotal : 0,
      sample_rate: recoveryRate(
        bankRows.filter((row) => row.recovery_status === "RECOVERED").length,
        bankRows.length,
      ),
      other_rate: recoveryRate(
        otherRows.filter((row) => row.recovery_status === "RECOVERED").length,
        otherRows.length,
      ),
    },
    calendar: [...calendarMap.values()],
    festivals,
    compliance: {
      stopped_cases: dashboard.health.stopped,
      suppressed_revenue: snapshot.metrics.suppressed_revenue,
      harmful_retries_prevented: dashboard.lift.harmful_retries_prevented,
    },
    loss_leaders: lossLeaders,
    insights: [],
  };
  model.insights = buildInsights(model, snapshot.metrics.updated_at);
  return model;
}
