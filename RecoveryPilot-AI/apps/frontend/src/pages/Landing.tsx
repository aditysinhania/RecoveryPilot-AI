import { motion } from "framer-motion";
import {
  ArrowRight,
  Gavel,
  Play,
  Route,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Stethoscope,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { CountUpStat } from "@/components/landing/CountUpStat";
import { DemoModal } from "@/components/landing/DemoModal";
import {
  IMPACT,
  INTEGRATIONS,
  LANDING_INSIGHTS,
  MERCHANTS,
  SHOWCASE,
  SIM_KNOBS,
  STEPS,
  TESTIMONIALS,
  TRUST_BADGES,
} from "@/components/landing/data";
import { HeroPreview } from "@/components/landing/HeroPreview";
import { LandingFooter } from "@/components/landing/LandingFooter";
import { LandingNav } from "@/components/landing/LandingNav";
import { landingFade, landingLift } from "@/components/landing/motion";
import { ProductMock } from "@/components/landing/ProductMocks";
import { InsightCard } from "@/components/shared/InsightCard";

const STEP_ICONS = [Stethoscope, Gavel, Route, ScrollText];

/** Public marketing homepage. Authenticated users get an Open dashboard CTA. */
export default function LandingPage() {
  const { user, ready } = useAuth();
  const [demoOpen, setDemoOpen] = useState(false);
  const signedIn = Boolean(user);
  const primaryTo = !ready
    ? "/signup"
    : signedIn
      ? user?.onboarding_completed
        ? "/dashboard"
        : "/onboarding"
      : "/signup";
  const primaryLabel = signedIn
    ? user?.onboarding_completed
      ? "Open dashboard"
      : "Continue setup"
    : "Start Free Trial";

  return (
    <div className="landing-page relative min-h-screen overflow-x-hidden bg-canvas text-foreground">
      <div className="landing-grid pointer-events-none fixed inset-0" aria-hidden />
      <motion.div
        className="pointer-events-none fixed bottom-[-20%] left-1/2 h-[520px] w-[720px] -translate-x-1/2 rounded-full bg-ai/25 blur-[140px]"
        animate={{ opacity: [0.35, 0.55, 0.35], scale: [1, 1.06, 1] }}
        transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        aria-hidden
      />
      <motion.div
        className="pointer-events-none fixed top-10 right-[-10%] h-[280px] w-[280px] rounded-full bg-info/20 blur-[110px]"
        animate={{ opacity: [0.25, 0.45, 0.25] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        aria-hidden
      />

      <LandingNav
        signedIn={signedIn}
        primaryTo={primaryTo}
        primaryLabel={primaryLabel}
        onWatchDemo={() => setDemoOpen(true)}
      />

      <section className="relative mx-auto grid max-w-6xl gap-12 px-4 pb-20 pt-12 lg:grid-cols-2 lg:items-center lg:pt-16">
        <motion.div {...landingFade}>
          <span className="landing-glass inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-medium text-ai">
            <Sparkles size={12} aria-hidden />
            AI-powered payment recovery
          </span>
          <h1 className="mt-5 text-4xl font-extrabold tracking-tight md:text-6xl md:leading-[1.05]">
            Turn failed payments into{" "}
            <span className="bg-gradient-to-r from-ai via-info to-recovered bg-clip-text text-transparent">
              recovered revenue
            </span>{" "}
            with AI.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-muted">
            RecoveryPilot diagnoses Razorpay subscription failures, applies an RBI-compliant policy engine, plans a
            single bounded action, and executes it in Sandbox — with an audit trail ops can replay.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <Link
              to={primaryTo}
              className="landing-cta landing-cta-pulse inline-flex items-center gap-2 rounded-2xl px-5 py-2.5 text-sm font-semibold text-canvas"
            >
              {primaryLabel}
              <ArrowRight size={16} aria-hidden />
            </Link>
            <Link
              to="/demo"
              className="inline-flex items-center gap-2 rounded-2xl border border-ai/40 bg-ai-muted/40 px-5 py-2.5 text-sm font-semibold text-ai"
            >
              Try Live Demo
            </Link>
            <button
              type="button"
              onClick={() => setDemoOpen(true)}
              className="inline-flex items-center gap-2 rounded-2xl border border-white/15 bg-white/5 px-5 py-2.5 text-sm text-foreground backdrop-blur"
            >
              <Play size={14} aria-hidden />
              Watch 2-minute Demo
            </button>
          </div>
          <ul className="mt-6 flex flex-wrap gap-2">
            {TRUST_BADGES.map((badge) => (
              <li key={badge} className="landing-glass rounded-full px-3 py-1 text-[11px] text-muted">
                {badge}
              </li>
            ))}
          </ul>
        </motion.div>
        <HeroPreview />
      </section>

      <section id="trusted" className="relative border-y border-white/5 py-10">
        <div className="mx-auto max-w-6xl px-4">
          <p className="text-center text-xs uppercase tracking-[0.2em] text-muted">
            Trusted by modern subscription businesses
          </p>
          <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            {MERCHANTS.map((merchant) => (
              <div key={merchant.name} className="landing-glass rounded-2xl px-4 py-4 text-center">
                <p className="text-sm font-semibold">{merchant.name}</p>
                <p className="mt-1 text-[11px] text-muted">{merchant.category}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="relative mx-auto max-w-6xl px-4 py-20">
        <motion.div {...landingFade} className="max-w-2xl">
          <p className="text-xs uppercase tracking-[0.2em] text-ai">Business impact</p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight">FitLife seed-42, measured in integer paise.</h2>
        </motion.div>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {IMPACT.map((item) => (
            <motion.article key={item.label} {...landingFade} {...landingLift} className="landing-glass rounded-[24px] p-5">
              <p className="text-3xl font-extrabold tracking-tight text-ai">
                <CountUpStat
                  value={item.value}
                  prefix={"prefix" in item ? item.prefix : ""}
                  suffix={item.suffix}
                  decimals={item.decimals}
                />
              </p>
              <p className="mt-2 text-sm font-medium">{item.label}</p>
              <p className="mt-1 text-xs text-muted">{item.hint}</p>
            </motion.article>
          ))}
        </div>
      </section>

      <section id="features" className="relative border-y border-white/5 bg-canvas-muted/40 py-20">
        <div className="mx-auto max-w-6xl px-4">
          <motion.div {...landingFade}>
            <p className="text-xs uppercase tracking-[0.2em] text-ai">How RecoveryPilot works</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight">Four engines. One bounded recovery.</h2>
          </motion.div>
          <ol className="mt-10 grid gap-4 md:grid-cols-4">
            {STEPS.map((step, index) => {
              const Icon = STEP_ICONS[index] ?? Sparkles;
              return (
                <motion.li key={step.title} {...landingFade} {...landingLift} className="landing-glass rounded-[24px] p-5">
                  <Icon className="text-ai" size={20} aria-hidden />
                  <p className="mt-4 text-xs text-info">0{index + 1}</p>
                  <h3 className="mt-1 font-semibold">{step.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-muted">{step.body}</p>
                </motion.li>
              );
            })}
          </ol>
        </div>
      </section>

      <section id="product" className="relative mx-auto max-w-6xl space-y-20 px-4 py-20">
        {SHOWCASE.map((item, index) => (
          <motion.article
            key={item.id}
            {...landingFade}
            className={`grid items-center gap-10 lg:grid-cols-2 ${index % 2 === 1 ? "lg:[&>*:first-child]:order-2" : ""}`}
          >
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-ai">{item.kicker}</p>
              <h2 className="mt-2 text-3xl font-bold tracking-tight">{item.title}</h2>
              <p className="mt-3 text-sm leading-6 text-muted">{item.body}</p>
            </div>
            <ProductMock kind={item.mock} />
          </motion.article>
        ))}
      </section>

      <section id="simulator" className="relative border-y border-white/5 py-20">
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 lg:grid-cols-2">
          <motion.div {...landingFade}>
            <p className="text-xs uppercase tracking-[0.2em] text-ai">AI Simulator</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight">Replay recovery strategies before going live.</h2>
            <p className="mt-3 text-sm leading-6 text-muted">
              Same FitLife seed. Toggle salary-cycle NSF, bank downtime, festival congestion, and promise-to-pay.
              Compare RecoveryPilot against immediate retry without calling Razorpay or Gemini.
            </p>
            <ul className="mt-5 flex flex-wrap gap-2">
              {SIM_KNOBS.map((knob) => (
                <li key={knob} className="landing-glass rounded-full px-3 py-1 text-[11px] text-muted">
                  {knob}
                </li>
              ))}
            </ul>
            <Link to={signedIn ? "/simulator" : "/signup"} className="mt-6 inline-flex items-center gap-2 text-sm text-info">
              Open Simulator Lab <ArrowRight size={14} />
            </Link>
          </motion.div>
          <ProductMock kind="simulator" />
        </div>
      </section>

      <section className="relative mx-auto max-w-6xl px-4 py-20">
        <motion.div {...landingFade}>
          <p className="text-xs uppercase tracking-[0.2em] text-ai">Integrations</p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight">Wired for Sandbox, ready for ops.</h2>
        </motion.div>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {INTEGRATIONS.map((item) => (
            <motion.article key={item.name} {...landingFade} {...landingLift} className="landing-glass rounded-[24px] p-5">
              <h3 className="font-semibold">{item.name}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{item.body}</p>
            </motion.article>
          ))}
        </div>
      </section>

      <section id="insights" className="relative border-y border-white/5 bg-canvas-muted/40 py-20">
        <div className="mx-auto max-w-6xl px-4">
          <motion.div {...landingFade}>
            <p className="text-xs uppercase tracking-[0.2em] text-ai">AI insights</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight">The same cards operators see on the dashboard.</h2>
          </motion.div>
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            {LANDING_INSIGHTS.map((insight) => (
              <InsightCard key={insight.title} insight={insight} />
            ))}
          </div>
        </div>
      </section>

      <section id="stories" className="relative mx-auto max-w-6xl px-4 py-20">
        <motion.div {...landingFade}>
          <p className="text-xs uppercase tracking-[0.2em] text-ai">Social proof</p>
          <h2 className="mt-2 text-3xl font-bold tracking-tight">Merchant personas from the simulator lab.</h2>
        </motion.div>
        <div className="mt-8 grid gap-4 lg:grid-cols-3">
          {TESTIMONIALS.map((item) => (
            <motion.blockquote
              key={item.merchant}
              {...landingFade}
              {...landingLift}
              className="landing-glass rounded-[24px] p-6"
            >
              <p className="text-sm leading-6 text-foreground">“{item.quote}”</p>
              <footer className="mt-5">
                <p className="text-sm font-semibold">{item.merchant}</p>
                <p className="text-xs text-muted">{item.role}</p>
                <p className="mt-2 text-xs text-ai">{item.metric}</p>
              </footer>
            </motion.blockquote>
          ))}
        </div>
      </section>

      <section id="pricing" className="relative mx-auto max-w-6xl px-4 pb-8">
        <motion.div {...landingFade} className="landing-glass landing-gradient-border rounded-[28px] p-8 text-center md:p-12">
          <ShieldCheck className="mx-auto text-ai" size={28} aria-hidden />
          <h2 className="mt-4 text-3xl font-bold tracking-tight md:text-4xl">Ready to recover more revenue?</h2>
          <p className="mx-auto mt-3 max-w-xl text-sm text-muted">
            No credit card. Two-minute setup. Demo workspace included — import FitLife or start empty after onboarding.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link
              to={primaryTo}
              className="landing-cta landing-cta-pulse rounded-2xl px-5 py-2.5 text-sm font-semibold text-canvas"
            >
              Start Free Trial
            </Link>
            <Link to="/demo" className="rounded-2xl border border-ai/40 bg-ai-muted/40 px-5 py-2.5 text-sm font-semibold text-ai">
              Try Live Demo
            </Link>
            <button
              type="button"
              onClick={() => setDemoOpen(true)}
              className="rounded-2xl border border-white/15 px-5 py-2.5 text-sm"
            >
              Watch Demo
            </button>
          </div>
          <p className="mt-4 text-xs text-muted">Hackathon sandbox is free. Razorpay capture stays with Razorpay.</p>
        </motion.div>
      </section>

      <section id="docs" className="relative mx-auto max-w-6xl px-4 py-16">
        <div className="grid gap-6 md:grid-cols-3">
          <article className="landing-glass rounded-[24px] p-5">
            <h3 className="font-semibold">Architecture</h3>
            <p className="mt-2 text-sm text-muted">
              Thin FastAPI routers. Domain in <code>services/</code>. Razorpay and Gemini in <code>integrations/</code>.
            </p>
          </article>
          <article className="landing-glass rounded-[24px] p-5" id="architecture">
            <h3 className="font-semibold">Auth &amp; API</h3>
            <p className="mt-2 text-sm text-muted">
              JWT shell on <code>/api/v1/auth</code>. OpenAPI at the FastAPI <code>/docs</code> when the API is running.
            </p>
          </article>
          <article className="landing-glass rounded-[24px] p-5" id="faq">
            <h3 className="font-semibold">Does it charge cards?</h3>
            <p className="mt-2 text-sm text-muted">
              No. Sandbox payment links and mandate sessions only. Diagnosis, policy, and planner are unchanged.
            </p>
          </article>
        </div>
        <div className="mt-8 grid gap-4 text-xs text-muted md:grid-cols-2">
          <p id="privacy">
            <span className="font-semibold text-foreground">Privacy. </span>
            Passwords are bcrypt hashes. Refresh tokens are hashed. Access JWTs are not stored. Secrets are never logged.
          </p>
          <p id="terms">
            <span className="font-semibold text-foreground">Terms. </span>
            Sandbox evaluation only. Integer paise. Promote live Razorpay keys when your merchant is ready.
          </p>
        </div>
      </section>

      <LandingFooter />
      <DemoModal open={demoOpen} onClose={() => setDemoOpen(false)} primaryTo={primaryTo} />
    </div>
  );
}
