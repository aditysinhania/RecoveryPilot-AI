import { formatPaise, formatPercent, titleCase } from "@/lib/format";
import { SNAPSHOT } from "@/services/dashboard";
import type { MixRow, PaymentMixRow, StatusStackRow, StrategyRow } from "@/types/analytics";
import type { DashboardInsight, FunnelStage, TrendPoint } from "@/types/dashboard";
import type {
  BaselineStrategy,
  LabKpis,
  MerchantKey,
  MerchantProfileView,
  ScenarioControls,
  ScenarioDelta,
  ScenarioResult,
} from "@/types/simulatorLab";

const GYM_CUSTOMERS = SNAPSHOT.counts.customers;
const GYM_ATTEMPTS = SNAPSHOT.counts.payments;
const GYM_FAILED = SNAPSHOT.counts.failed_payments;
const GYM_FAILURE_RATE = GYM_FAILED / GYM_ATTEMPTS;
const GYM_ARPU =
  0.38 * 49_900 + 0.32 * 99_900 + 0.2 * 149_900 + 0.1 * 249_900;

const NSF = SNAPSHOT.failure_reasons.find((item) => item.key === "INSUFFICIENT_FUNDS");
const NSF_SHARE = NSF ? NSF.revenue_paise / SNAPSHOT.metrics.revenue_at_risk : 0.43;

export const MERCHANT_PROFILES: Record<MerchantKey, MerchantProfileView> = {
  gym: {
    key: "gym",
    label: "FitLife Gym",
    merchant_name: "FitLife Gym",
    business_category: "Fitness & Wellness",
    notes: "Bangalore gym. Salary-cycle NSF. Default hackathon dataset.",
    arpu_paise: GYM_ARPU,
    festival_default: false,
    method_weights: { UPI: 0.62, CARD: 0.22, NETBANKING: 0.1, WALLET: 0.06 },
    segment_weights: {
      HIGH_VALUE: 0.1,
      LOYAL: 0.3,
      ACTIVE: 0.25,
      NEW: 0.15,
      AT_RISK: 0.12,
      CHURN_RISK: 0.08,
    },
  },
  saas: {
    key: "saas",
    label: "SaaS",
    merchant_name: "CloudLedger",
    business_category: "B2B SaaS",
    notes: "B2B invoicing. Card-heavy, annual plans, sticky payers.",
    arpu_paise: 0.22 * 99_900 + 0.38 * 249_900 + 0.28 * 499_900 + 0.12 * 999_900,
    festival_default: false,
    method_weights: { UPI: 0.28, CARD: 0.48, NETBANKING: 0.2, WALLET: 0.04 },
    segment_weights: {
      HIGH_VALUE: 0.18,
      LOYAL: 0.34,
      ACTIVE: 0.22,
      NEW: 0.12,
      AT_RISK: 0.08,
      CHURN_RISK: 0.06,
    },
  },
  ott: {
    key: "ott",
    label: "OTT",
    merchant_name: "StreamBox",
    business_category: "OTT / Media",
    notes: "Low ARPU, wallet + UPI, higher churn, festival binge windows.",
    arpu_paise: 0.4 * 14_900 + 0.32 * 19_900 + 0.18 * 49_900 + 0.1 * 64_900,
    festival_default: true,
    method_weights: { UPI: 0.58, CARD: 0.16, NETBANKING: 0.06, WALLET: 0.2 },
    segment_weights: {
      HIGH_VALUE: 0.06,
      LOYAL: 0.2,
      ACTIVE: 0.3,
      NEW: 0.18,
      AT_RISK: 0.14,
      CHURN_RISK: 0.12,
    },
  },
  edtech: {
    key: "edtech",
    label: "EdTech",
    merchant_name: "LearnHub Academy",
    business_category: "EdTech",
    notes: "Exam-season and festival UPI congestion. Parent salary cycles.",
    arpu_paise: 0.42 * 29_900 + 0.3 * 59_900 + 0.18 * 99_900 + 0.1 * 149_900,
    festival_default: true,
    method_weights: { UPI: 0.72, CARD: 0.14, NETBANKING: 0.06, WALLET: 0.08 },
    segment_weights: {
      HIGH_VALUE: 0.08,
      LOYAL: 0.22,
      ACTIVE: 0.28,
      NEW: 0.22,
      AT_RISK: 0.12,
      CHURN_RISK: 0.08,
    },
  },
};

export const DEFAULT_CONTROLS: ScenarioControls = {
  merchant: "gym",
  customerCount: GYM_CUSTOMERS,
  failureRate: GYM_FAILURE_RATE,
  salaryCycle: true,
  festivalCalendar: false,
  bankDowntime: false,
  promiseToPay: true,
  baselineStrategy: "immediate_retry",
  seed: 42,
};

const STRATEGY_BY_REASON: Record<string, string> = {
  INSUFFICIENT_FUNDS: "WAIT_FOR_PAYDAY",
  UPI_FAILURE: "RETRY_SILENTLY",
  BANK_TIMEOUT: "RETRY_SILENTLY",
  CARD_EXPIRED: "SWITCH_PAYMENT_METHOD",
  MANDATE_REVOKED: "REQUEST_NEW_MANDATE",
  OTHER: "STOP_RECOVERY",
};

const SMS_COST = 15;

function clampSummary(text: string): string {
  if (text.length <= 160) {
    return text;
  }
  return `${text.slice(0, 157)}...`;
}

function mulberry32(seed: number): () => number {
  let t = seed >>> 0;
  return (): number => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

function roundPaise(value: number): number {
  return Math.round(value);
}

function rate(recovered: number, atRisk: number): number {
  if (atRisk <= 0) {
    return 0;
  }
  return recovered / atRisk;
}

/** True when knobs match the FitLife seed-42 snapshot bit-for-bit. */
export function isDefaultFitlife(controls: ScenarioControls): boolean {
  return (
    controls.merchant === "gym" &&
    controls.customerCount === GYM_CUSTOMERS &&
    Math.abs(controls.failureRate - GYM_FAILURE_RATE) < 1e-9 &&
    controls.salaryCycle &&
    !controls.festivalCalendar &&
    !controls.bankDowntime &&
    controls.promiseToPay &&
    controls.baselineStrategy === "immediate_retry" &&
    controls.seed === 42
  );
}

/** True when two control snapshots are equal. */
export function controlsEqual(a: ScenarioControls, b: ScenarioControls): boolean {
  return (
    a.merchant === b.merchant &&
    a.customerCount === b.customerCount &&
    Math.abs(a.failureRate - b.failureRate) < 1e-9 &&
    a.salaryCycle === b.salaryCycle &&
    a.festivalCalendar === b.festivalCalendar &&
    a.bankDowntime === b.bankDowntime &&
    a.promiseToPay === b.promiseToPay &&
    a.baselineStrategy === b.baselineStrategy &&
    a.seed === b.seed
  );
}

/** Short chip label for a merchant + volume scenario. */
export function scenarioLabel(controls: ScenarioControls): string {
  const profile = MERCHANT_PROFILES[controls.merchant];
  return `${profile.merchant_name} · ${controls.customerCount.toLocaleString("en-IN")} cust · ${formatPercent(controls.failureRate, 0)} fail`;
}

/** Human name for a baseline strategy. */
export function baselineLabel(strategy: BaselineStrategy): string {
  if (strategy === "wait_three_days") {
    return "Wait 3 days then retry";
  }
  if (strategy === "payday_only") {
    return "Payday-only retry";
  }
  return "Immediate retry";
}

function emptyKpis(): LabKpis {
  return {
    revenue_at_risk: 0,
    revenue_recovered: 0,
    recovery_rate: 0,
    ai_lift: 0,
    harmful_retries_prevented: 0,
    compliance_savings: 0,
    communication_cost: 0,
  };
}

function makeKpis(partial: Partial<LabKpis> & Pick<LabKpis, "revenue_at_risk" | "revenue_recovered">): LabKpis {
  const next = { ...emptyKpis(), ...partial };
  next.recovery_rate = rate(next.revenue_recovered, next.revenue_at_risk);
  return next;
}

function scaleFunnel(funnel: FunnelStage[], volume: number, arpu: number): FunnelStage[] {
  return funnel.map((stage) => ({
    stage: stage.stage,
    count: Math.max(0, Math.round(stage.count * volume)),
    revenue_paise: roundPaise(stage.revenue_paise * volume * arpu),
  }));
}

function diagnosisFromSnapshot(volume: number, arpu: number, salaryCycle: boolean, bankBoost: number): StatusStackRow[] {
  const total = SNAPSHOT.counts.recovery_cases;
  const recoveredShare = SNAPSHOT.recovery_summary.recovered_cases / total;
  const waitingShare = SNAPSHOT.health.cases_waiting / total;
  const escalatedShare = SNAPSHOT.health.escalated / total;
  const stoppedShare = SNAPSHOT.health.stopped / total;
  return SNAPSHOT.failure_reasons.map((slice) => {
    const nsfCut = slice.key === "INSUFFICIENT_FUNDS" && !salaryCycle ? 0.18 : 1;
    const bankCut = slice.key === "BANK_TIMEOUT" ? bankBoost : 1;
    const count = Math.max(0, Math.round(slice.count * volume * bankCut));
    const recovered = Math.max(0, Math.round(count * recoveredShare * nsfCut));
    const waiting = Math.max(0, Math.round(count * waitingShare));
    const escalated = Math.max(0, Math.round(count * escalatedShare));
    const stopped = Math.max(0, Math.round(count * stoppedShare * (salaryCycle ? 1 : 0.7)));
    const open = Math.max(0, count - recovered - waiting - escalated - stopped);
    return {
      key: slice.key,
      label: slice.label,
      recovered,
      waiting,
      escalated,
      stopped,
      open,
      revenue_paise: roundPaise(slice.revenue_paise * volume * arpu * bankCut),
    };
  });
}

function strategiesFromDiagnosis(rows: StatusStackRow[]): StrategyRow[] {
  const buckets = new Map<string, StrategyRow>();
  for (const row of rows) {
    const key = STRATEGY_BY_REASON[row.key] ?? "RETRY_PAYMENT";
    const current = buckets.get(key) ?? {
      key,
      label: titleCase(key),
      recovered: 0,
      remaining: 0,
      recovered_paise: 0,
      rate: 0,
    };
    current.recovered += row.recovered;
    current.remaining += row.waiting + row.open + row.escalated + row.stopped;
    const recoveredShare = row.recovered + row.waiting + row.open + row.escalated + row.stopped;
    current.recovered_paise += recoveredShare > 0 ? Math.round(row.revenue_paise * (row.recovered / recoveredShare)) : 0;
    buckets.set(key, current);
  }
  return [...buckets.values()].map((row) => ({
    ...row,
    rate: rate(row.recovered, row.recovered + row.remaining),
  }));
}

function segmentsFromProfile(
  profile: MerchantProfileView,
  cases: number,
  atRisk: number,
  recovered: number,
  volume: number,
): MixRow[] {
  return Object.entries(profile.segment_weights).map(([key, weight]) => {
    const count = Math.max(0, Math.round(cases * weight));
    const revenue = roundPaise(atRisk * weight);
    const recoveredCount = Math.max(0, Math.round(SNAPSHOT.recovery_summary.recovered_cases * volume * weight));
    const recoveredPaise = roundPaise(recovered * weight);
    return {
      key,
      label: titleCase(key),
      count,
      recovered: recoveredCount,
      revenue_paise: revenue,
      recovered_paise: recoveredPaise,
    };
  });
}

function methodsFromProfile(profile: MerchantProfileView, cases: number, atRisk: number): PaymentMixRow[] {
  const gym = MERCHANT_PROFILES.gym.method_weights;
  return Object.entries(profile.method_weights).map(([key, weight]) => {
    const gymWeight = gym[key] ?? weight;
    const tilt = weight / gymWeight;
    const recoveredShare = Math.min(0.95, SNAPSHOT.metrics.recovery_rate * (0.85 + 0.15 * tilt));
    const count = Math.max(0, Math.round(cases * weight));
    const recoveredCount = Math.max(0, Math.round(count * recoveredShare));
    return {
      key,
      label: key,
      recovered: recoveredCount,
      failed: Math.max(0, count - recoveredCount),
      revenue_paise: roundPaise(atRisk * weight),
    };
  });
}

function scaleTrend(volume: number, arpu: number, aiFactor: number, baselineFactor: number): TrendPoint[] {
  return SNAPSHOT.trend.map((point) => ({
    date: point.date,
    recovered_paise: roundPaise(point.recovered_paise * volume * arpu * aiFactor),
    recovered_count: Math.max(0, Math.round(point.recovered_count * volume * aiFactor)),
    baseline_paise: roundPaise((point.baseline_paise || point.recovered_paise * 0.49) * volume * arpu * baselineFactor),
  }));
}

function buildInsights(result: Omit<ScenarioResult, "insights">): DashboardInsight[] {
  const generatedAt = result.generated_at;
  const top = [...result.diagnosis].sort((a, b) => b.revenue_paise - a.revenue_paise)[0];
  const best = [...result.strategies].sort((a, b) => b.recovered_paise - a.recovered_paise || b.rate - a.rate)[0];
  const lift = result.ai.ai_lift;
  const leak = top
    ? `${top.label} is ${formatPaise(top.revenue_paise)} at risk (${top.recovered} recovered in this mix).`
    : "Diagnosis mix is balanced across this scenario.";
  return [
    {
      title: top ? `${top.label} is the biggest revenue leak` : "No dominant leak",
      summary: clampSummary(leak),
      risk_level: top && top.key === "INSUFFICIENT_FUNDS" ? "HIGH" : "MEDIUM",
      next_action: result.controls.salaryCycle
        ? "Keep NSF on payday wait — do not blast retries."
        : "Turn salary-cycle waits on; immediate NSF retries recover almost nothing.",
      source: "fallback",
      cached: true,
      generated_at: generatedAt,
    },
    {
      title: best ? `Lead with ${best.label}` : "Planner mix is thin",
      summary: clampSummary(
        best
          ? `${best.label} recovered ${best.recovered} of ${best.recovered + best.remaining} cases (${formatPercent(best.rate)}).`
          : "Not enough mix to rank planner strategies.",
      ),
      risk_level: "MEDIUM",
      next_action: "Protect high-performing strategies in policy.",
      source: "fallback",
      cached: true,
      generated_at: generatedAt,
    },
    {
      title: result.controls.bankDowntime
        ? "Bank downtime raises compliance risk"
        : "Stopping rules are the compliance win",
      summary: clampSummary(
        `Policy suppresses ${formatPaise(result.ai.compliance_savings)} and prevents ${result.ai.harmful_retries_prevented} harmful retries. Baseline still retries already-paid, dispute, revoked, and cancelled invoices.`,
      ),
      risk_level: result.controls.bankDowntime ? "HIGH" : "MEDIUM",
      next_action: "Do not retry during NPCI / issuer outages.",
      source: "fallback",
      cached: true,
      generated_at: generatedAt,
    },
    {
      title: `Expected improvement ${formatPaise(lift)}`,
      summary: clampSummary(
        `RecoveryPilot recovers ${formatPercent(result.ai.recovery_rate)} versus ${formatPercent(result.baseline.recovery_rate)} ${baselineLabel(result.controls.baselineStrategy).toLowerCase()}. Extra rupees ${formatPaise(lift)}.`,
      ),
      risk_level: lift > 0 ? "LOW" : "HIGH",
      next_action: "Save this scenario and compare it with seed 42.",
      source: "fallback",
      cached: true,
      generated_at: generatedAt,
    },
  ];
}

/**
 * Recompute a playground scenario from the seed-42 FitLife snapshot.
 * Does not call engines, Gemini, Razorpay, or new HTTP routes.
 */
export function runScenario(controls: ScenarioControls, generatedAt = new Date().toISOString()): ScenarioResult {
  const profile = MERCHANT_PROFILES[controls.merchant];
  const volume = (controls.customerCount / GYM_CUSTOMERS) * (controls.failureRate / GYM_FAILURE_RATE);
  const arpu = profile.arpu_paise / GYM_ARPU;
  const rng = mulberry32(controls.seed);
  const jitter = controls.seed === 42 ? 1 : 0.97 + rng() * 0.06;

  let atRisk = SNAPSHOT.metrics.revenue_at_risk;
  let aiRecovered = SNAPSHOT.metrics.recovered_revenue;
  let baselineRecovered = SNAPSHOT.baseline.recovered_revenue;
  let harmful = SNAPSHOT.harmful_retries_prevented;
  let suppressed = SNAPSHOT.metrics.suppressed_revenue;
  let aiCost = SNAPSHOT.communication_costs.ai_total_paise;
  let baselineCost = SNAPSHOT.communication_costs.baseline_total_paise;
  let cases = GYM_FAILED;
  let bankBoost = 1;
  let aiTrend = 1;
  let baselineTrend = 1;

  if (!controls.salaryCycle) {
    const nsfLift = SNAPSHOT.lift_recovered_revenue * NSF_SHARE;
    aiRecovered = Math.max(baselineRecovered, aiRecovered - nsfLift);
    aiTrend *= aiRecovered / SNAPSHOT.metrics.recovered_revenue;
  }
  if (controls.festivalCalendar) {
    atRisk = roundPaise(atRisk * 1.04);
    aiRecovered = roundPaise(aiRecovered * 0.985);
    baselineRecovered = roundPaise(baselineRecovered * 1.06);
    aiCost = roundPaise(aiCost * 1.08);
    aiTrend *= 0.985;
    baselineTrend *= 1.06;
  }
  if (controls.bankDowntime) {
    atRisk = roundPaise(atRisk * 1.06);
    aiRecovered = roundPaise(aiRecovered * 0.99);
    harmful = Math.round(harmful * 1.22);
    suppressed = roundPaise(suppressed * 1.15);
    bankBoost = 1.35;
    aiTrend *= 0.99;
  }
  if (!controls.promiseToPay) {
    aiRecovered = roundPaise(aiRecovered * 0.92);
    aiTrend *= 0.92;
    aiCost = roundPaise(aiCost * 0.88);
  }
  if (controls.baselineStrategy === "wait_three_days") {
    const nsfAtRisk = SNAPSHOT.metrics.revenue_at_risk * NSF_SHARE;
    baselineRecovered = roundPaise(baselineRecovered + nsfAtRisk * 0.35);
    baselineTrend *= baselineRecovered / SNAPSHOT.baseline.recovered_revenue;
  }
  if (controls.baselineStrategy === "payday_only") {
    const nsfLift = SNAPSHOT.lift_recovered_revenue * NSF_SHARE;
    baselineRecovered = roundPaise(baselineRecovered + nsfLift * 0.8);
    harmful = Math.round(harmful * 0.55);
    baselineTrend *= baselineRecovered / SNAPSHOT.baseline.recovered_revenue;
  }

  const scale = volume * arpu * jitter;
  atRisk = roundPaise(atRisk * scale);
  aiRecovered = roundPaise(aiRecovered * scale);
  baselineRecovered = roundPaise(baselineRecovered * scale);
  suppressed = roundPaise(suppressed * scale);
  aiCost = roundPaise(aiCost * volume * jitter);
  cases = Math.max(1, Math.round(GYM_FAILED * volume * jitter));
  harmful = Math.max(0, Math.round(harmful * volume * jitter));
  baselineCost = cases * SMS_COST;
  aiRecovered = Math.min(atRisk, Math.max(0, aiRecovered));
  baselineRecovered = Math.min(atRisk, Math.max(0, baselineRecovered));

  if (isDefaultFitlife(controls)) {
    atRisk = SNAPSHOT.metrics.revenue_at_risk;
    aiRecovered = SNAPSHOT.metrics.recovered_revenue;
    baselineRecovered = SNAPSHOT.baseline.recovered_revenue;
    harmful = SNAPSHOT.harmful_retries_prevented;
    suppressed = SNAPSHOT.metrics.suppressed_revenue;
    aiCost = SNAPSHOT.communication_costs.ai_total_paise;
    baselineCost = SNAPSHOT.communication_costs.baseline_total_paise;
    cases = GYM_FAILED;
    bankBoost = 1;
    aiTrend = 1;
    baselineTrend = 1;
  }

  const lift = aiRecovered - baselineRecovered;
  const ai = makeKpis({
    revenue_at_risk: atRisk,
    revenue_recovered: aiRecovered,
    ai_lift: lift,
    harmful_retries_prevented: harmful,
    compliance_savings: suppressed,
    communication_cost: aiCost,
  });
  const baseline = makeKpis({
    revenue_at_risk: atRisk,
    revenue_recovered: baselineRecovered,
    ai_lift: 0,
    harmful_retries_prevented: 0,
    compliance_savings: 0,
    communication_cost: baselineCost,
  });

  const funnelAi = isDefaultFitlife(controls)
    ? SNAPSHOT.funnel.map((stage) => ({ ...stage }))
    : scaleFunnel(SNAPSHOT.funnel, volume * jitter, arpu).map((stage, index, list) => {
        if (index === list.length - 1) {
          return { ...stage, count: Math.round(cases * ai.recovery_rate), revenue_paise: aiRecovered };
        }
        if (index === 0) {
          return { ...stage, count: cases, revenue_paise: atRisk };
        }
        return stage;
      });
  const funnelBaseline: FunnelStage[] = [
    { stage: "At Risk", count: cases, revenue_paise: atRisk },
    { stage: "Diagnosed", count: cases, revenue_paise: atRisk },
    { stage: "Retried", count: cases, revenue_paise: atRisk },
    {
      stage: "Recovered",
      count: Math.round(cases * baseline.recovery_rate),
      revenue_paise: baselineRecovered,
    },
  ];

  const diagnosis = diagnosisFromSnapshot(volume * jitter, arpu, controls.salaryCycle, bankBoost);
  const strategies = strategiesFromDiagnosis(diagnosis);
  const customers = Math.round(controls.customerCount * (controls.seed === 42 ? 1 : jitter));
  const result: ScenarioResult = {
    id: `${controls.merchant}-${controls.seed}-${controls.customerCount}`,
    controls: { ...controls },
    label: scenarioLabel(controls),
    generated_at: isDefaultFitlife(controls) ? SNAPSHOT.metrics.updated_at : generatedAt,
    source: isDefaultFitlife(controls) ? "snapshot" : "scenario",
    cases,
    customers,
    ai,
    baseline,
    funnel_ai: funnelAi,
    funnel_baseline: funnelBaseline,
    diagnosis,
    strategies,
    segments: segmentsFromProfile(profile, cases, atRisk, aiRecovered, volume * jitter),
    methods: methodsFromProfile(profile, cases, atRisk),
    trend: isDefaultFitlife(controls) ? SNAPSHOT.trend.map((point) => ({ ...point })) : scaleTrend(volume * jitter, arpu, aiTrend, baselineTrend),
    insights: [],
  };
  result.insights = buildInsights(result);
  return result;
}

export const SEED_42_RESULT: ScenarioResult = runScenario(DEFAULT_CONTROLS, SNAPSHOT.metrics.updated_at);

const KPI_META: { key: keyof LabKpis; label: string; kind: ScenarioDelta["kind"]; higher_is_better: boolean }[] = [
  { key: "revenue_at_risk", label: "Revenue at Risk", kind: "paise", higher_is_better: false },
  { key: "revenue_recovered", label: "Revenue Recovered", kind: "paise", higher_is_better: true },
  { key: "recovery_rate", label: "Recovery Rate", kind: "rate", higher_is_better: true },
  { key: "ai_lift", label: "AI Lift", kind: "paise", higher_is_better: true },
  { key: "harmful_retries_prevented", label: "Harmful Retries Prevented", kind: "count", higher_is_better: true },
  { key: "compliance_savings", label: "Compliance Savings", kind: "paise", higher_is_better: true },
  { key: "communication_cost", label: "Communication Cost", kind: "paise", higher_is_better: false },
];

/** Metric-by-metric AI minus baseline for the comparison drawer. */
export function kpiDeltas(ai: LabKpis, baseline: LabKpis): ScenarioDelta[] {
  return KPI_META.map((meta) => ({
    key: meta.key,
    label: meta.label,
    ai: ai[meta.key],
    baseline: baseline[meta.key],
    delta: ai[meta.key] - baseline[meta.key],
    kind: meta.kind,
    higher_is_better: meta.higher_is_better,
  }));
}

/** Seed-42 versus current-run deltas (AI column of each). */
export function scenarioDeltas(current: ScenarioResult, reference: ScenarioResult = SEED_42_RESULT): ScenarioDelta[] {
  return kpiDeltas(current.ai, reference.ai).map((row) => ({
    ...row,
    ai: current.ai[row.key],
    baseline: reference.ai[row.key],
    delta: current.ai[row.key] - reference.ai[row.key],
  }));
}

/** Chip list for the scenario summary strip. */
export function conditionChips(controls: ScenarioControls): { label: string; active: boolean }[] {
  const profile = MERCHANT_PROFILES[controls.merchant];
  return [
    { label: profile.merchant_name, active: true },
    { label: `${controls.customerCount.toLocaleString("en-IN")} customers`, active: true },
    { label: `${formatPercent(controls.failureRate, 0)} failure rate`, active: true },
    { label: "Salary cycle", active: controls.salaryCycle },
    { label: "Festival calendar", active: controls.festivalCalendar },
    { label: "NPCI / bank downtime", active: controls.bankDowntime },
    { label: "Promise-to-pay", active: controls.promiseToPay },
    { label: baselineLabel(controls.baselineStrategy), active: true },
    { label: `Seed ${controls.seed}`, active: true },
  ];
}
