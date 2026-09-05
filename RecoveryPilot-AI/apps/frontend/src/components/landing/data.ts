import type { DashboardInsight } from "@/types/dashboard";

export const NAV_LINKS = [
  { href: "#product", label: "Product" },
  { href: "#features", label: "Features" },
  { href: "#simulator", label: "Simulator" },
  { href: "#docs", label: "Docs" },
  { href: "#pricing", label: "Pricing" },
] as const;

export const TRUST_BADGES = [
  "Works with Razorpay Sandbox",
  "RBI-compliant recovery policies",
  "AI-powered recovery decisions",
] as const;

export const MERCHANTS = [
  { name: "FitLife Gym", category: "Fitness" },
  { name: "LearnHub", category: "EdTech" },
  { name: "CloudLedger", category: "B2B SaaS" },
  { name: "StreamBox", category: "OTT" },
] as const;

export const IMPACT = [
  { value: 69.3, suffix: "%", label: "Recovery rate", hint: "FitLife seed-42 cohort", decimals: 1 },
  { value: 5.83, prefix: "₹", suffix: "L", label: "Revenue recovered", hint: "Integer paise, never floats", decimals: 2 },
  { value: 117, suffix: "", label: "Harmful retries prevented", hint: "Policy stops on revoked / dispute", decimals: 0 },
  { value: 500, suffix: "+", label: "Webhook events processed", hint: "HMAC-verified inbox", decimals: 0 },
] as const;

export const STEPS = [
  {
    title: "Diagnose failure",
    body: "Gemini-shaped diagnosis scores NSF, mandate, UPI, and instrument failures with evidence — not a chatbot reply.",
  },
  {
    title: "Apply RBI policy",
    body: "Consent, frequency, and rupee caps sit in front of every action. Stops are first-class audit events.",
  },
  {
    title: "Plan best recovery",
    body: "WAIT, RETRY, LINK, or PROMISE — never both. Payday waits beat blast retries on salary-cycle NSF.",
  },
  {
    title: "Execute & audit",
    body: "Sandbox payment links and mandate sessions with idempotency keys. Ops can replay the trail.",
  },
] as const;

export const SHOWCASE = [
  {
    id: "dashboard",
    kicker: "Merchant cockpit",
    title: "See at-risk revenue, AI lift, and policy health in one glance.",
    body: "FitLife seed-42 KPIs, orchestrator queues, and Gemini-shaped insights without leaving integer paise.",
    mock: "dashboard" as const,
  },
  {
    id: "queue",
    kicker: "Recovery queue",
    title: "Prioritised cases with diagnosis, plan, and executor cards.",
    body: "Operators open a drawer for evidence, policy gates, and the next bounded action — not a spreadsheet dump.",
    mock: "queue" as const,
  },
  {
    id: "analytics",
    kicker: "Analytics",
    title: "Funnel, failure mix, and calendar-aware recovery windows.",
    body: "NSF share, payday lift, and festival bias stay visible so finance can defend the strategy.",
    mock: "analytics" as const,
  },
  {
    id: "audit",
    kicker: "Audit timeline",
    title: "Every allow, wait, and stop is replayable.",
    body: "HMAC webhooks, policy evaluations, and executor outcomes share a correlation id your compliance team can export.",
    mock: "audit" as const,
  },
  {
    id: "simulator",
    kicker: "Simulator Lab",
    title: "Replay recovery strategies before going live.",
    body: "Toggle salary-cycle, bank downtime, festivals, and promise-to-pay. Compare AI against immediate retry on the same seed.",
    mock: "simulator" as const,
  },
] as const;

export const SIM_KNOBS = [
  "Salary-cycle NSF",
  "Bank downtime",
  "Festival UPI congestion",
  "Promise-to-pay",
  "AI vs immediate retry",
] as const;

export const INTEGRATIONS = [
  { name: "Razorpay Sandbox", body: "Payment links, mandate updates, HMAC webhooks. Capture stays with Razorpay." },
  { name: "Gemini AI", body: "Structured diagnosis and operator copy. Never invents a charge." },
  { name: "PostgreSQL", body: "System of record for cases, sessions, and bcrypt hashes." },
  { name: "Redis scheduler", body: "Provisioned for WAIT_FOR_PAYDAY ticks. Not on the money path." },
  { name: "Sentry", body: "Business auth errors stay out of noise. Unhandled 500s are redacted." },
  { name: "Docker", body: "Postgres, API, and nginx in compose. Same stack from laptop to VPS." },
] as const;

export const LANDING_INSIGHTS: DashboardInsight[] = [
  {
    title: "NSF still dominates at-risk revenue",
    summary: "Insufficient funds is the largest slice of failed FitLife invoices. Payday waits recover more than immediate retries.",
    risk_level: "HIGH",
    next_action: "Keep NSF cases on payday wait — do not blast retries.",
    source: "fallback",
    cached: true,
    generated_at: "2026-09-02T18:00:00+05:30",
  },
  {
    title: "Wait-for-payday is the strongest strategy",
    summary: "RecoveryPilot recovers 69.3% versus 34.1% immediate-retry baseline — a 35.2 point lift on seed 42.",
    risk_level: "MEDIUM",
    next_action: "Protect stopping rules on revoked mandates and disputes.",
    source: "fallback",
    cached: true,
    generated_at: "2026-09-02T18:00:00+05:30",
  },
  {
    title: "Policy engine prevents harmful retries",
    summary: "117 harmful retries were suppressed on revoked, dispute, and already-paid cases. Stops are audit events.",
    risk_level: "LOW",
    next_action: "Review STOP vs ALLOW ratio in the audit explorer.",
    source: "fallback",
    cached: true,
    generated_at: "2026-09-02T18:00:00+05:30",
  },
  {
    title: "Compliance savings on the recovery path",
    summary: "Idempotency keys, HMAC verification, and integer paise keep RBI-shaped policy in front of every Razorpay call.",
    risk_level: "LOW",
    next_action: "Replay a correlation id before promoting Sandbox keys.",
    source: "fallback",
    cached: true,
    generated_at: "2026-09-02T18:00:00+05:30",
  },
];

export const TESTIMONIALS = [
  {
    merchant: "FitLife Gym",
    role: "Head of Billing, Bangalore",
    quote:
      "Payday waits recovered members we used to hammer with retries. Ops can finally show finance an audit trail, not a WhatsApp screenshot.",
    metric: "69.3% recovery rate",
  },
  {
    merchant: "LearnHub",
    role: "Collections lead, EdTech",
    quote:
      "Festival UPI congestion used to look like churn. The simulator showed us to wait, not escalate. Parents paid on salary week.",
    metric: "Policy-first, not blast-retry",
  },
  {
    merchant: "CloudLedger",
    role: "Founder, B2B SaaS",
    quote:
      "Annual card plans and sticky payers. RecoveryPilot stopped retrying revoked mandates. Compliance is a product feature, not a slide.",
    metric: "Harmful retries contained",
  },
] as const;

export const QUEUE_ROWS = [
  { name: "Rajesh Mehta", plan: "FitLife Pro", amount: "₹999", status: "Promise", diagnosis: "NSF" },
  { name: "Meera Menon", plan: "FitLife Pro", amount: "₹999", status: "Waiting", diagnosis: "NSF" },
  { name: "Varun Joshi", plan: "Premium", amount: "₹1,499", status: "Diagnosed", diagnosis: "UPI" },
  { name: "Rohan Iyer", plan: "Elite", amount: "₹2,499", status: "Recovered", diagnosis: "Card" },
] as const;

export const AUDIT_EVENTS = [
  { actor: "Policy Engine", summary: "Allow bounded recovery", tone: "recovered" },
  { actor: "Planner", summary: "WAIT_FOR_PAYDAY selected", tone: "ai" },
  { actor: "Executor", summary: "Payment link sent", tone: "info" },
  { actor: "Scheduler", summary: "Retry after salary window", tone: "waiting" },
] as const;
