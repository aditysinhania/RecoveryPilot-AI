import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useDemoMode } from "@/demo/DemoContext";
import { isTourComplete, markTourComplete } from "@/lib/workspacePrefs";

interface TourStep {
  id: string;
  path: string;
  selector: string;
  title: string;
  body: string;
}

const STEPS: TourStep[] = [
  {
    id: "kpis",
    path: "/dashboard",
    selector: "[data-tour='kpis']",
    title: "Dashboard KPIs",
    body: "Revenue at risk, recovered by AI, and lift versus a dumb retry baseline — FitLife seed-42 in one glance.",
  },
  {
    id: "insights",
    path: "/dashboard",
    selector: "[data-tour='insights']",
    title: "AI Insights",
    body: "Diagnosis-shaped cards explain why payments failed and which bounded action RecoveryPilot would take next.",
  },
  {
    id: "queue",
    path: "/recovery-queue",
    selector: "[data-tour='queue']",
    title: "Recovery Queue",
    body: "Open every failed subscription. Inspect policy, planner, and execution without charging a real card.",
  },
  {
    id: "analytics",
    path: "/analytics",
    selector: "[data-tour='analytics']",
    title: "Analytics",
    body: "Funnels, rails, and payday calendars over the 90-day FitLife window. Charts never render blank.",
  },
  {
    id: "audit",
    path: "/audit",
    selector: "[data-tour='audit']",
    title: "Audit Timeline",
    body: "Replay diagnosis → policy → plan → webhook as a correlation-grouped trail judges can follow.",
  },
  {
    id: "simulator",
    path: "/simulator",
    selector: "[data-tour='simulator']",
    title: "Simulator Lab",
    body: "Twist NSF mix, payday, and bank downtime. The lab recomputes locally — engines stay untouched.",
  },
];

interface SpotlightRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

function measure(selector: string): SpotlightRect | null {
  const node = document.querySelector<HTMLElement>(selector);
  if (!node) {
    return null;
  }
  const box = node.getBoundingClientRect();
  if (box.width < 8 || box.height < 8) {
    return null;
  }
  return { top: box.top, left: box.left, width: box.width, height: box.height };
}

/** Spotlight walkthrough for first visits to /demo or /dashboard. */
export function ProductTour() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { isDemo, opsPath } = useDemoMode();
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<SpotlightRect | null>(null);

  const onLanding = pathname === "/" || pathname === "/login" || pathname === "/signup" || pathname === "/onboarding";
  const trigger = isDemo || pathname === "/dashboard";

  useEffect(() => {
    if (onLanding || isTourComplete() || !trigger) {
      return;
    }
    setOpen(true);
  }, [onLanding, trigger]);

  const step = STEPS[index];
  const last = index === STEPS.length - 1;

  const finish = useCallback(() => {
    markTourComplete();
    setOpen(false);
  }, []);

  useEffect(() => {
    if (!open || !step) {
      return;
    }
    const target = opsPath(step.path);
    if (pathname !== target && !(step.path === "/dashboard" && pathname === "/demo")) {
      navigate(target, { replace: false });
    }
  }, [open, step, pathname, opsPath, navigate]);

  useEffect(() => {
    if (!open || !step) {
      return;
    }
    let cancelled = false;
    const tick = (): void => {
      if (cancelled) {
        return;
      }
      const next = measure(step.selector);
      if (next) {
        setRect(next);
        return;
      }
      window.setTimeout(tick, 80);
    };
    tick();
    const onResize = (): void => setRect(measure(step.selector));
    window.addEventListener("resize", onResize);
    return () => {
      cancelled = true;
      window.removeEventListener("resize", onResize);
    };
  }, [open, step, pathname, index]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        finish();
      }
      if (event.key === "ArrowRight") {
        setIndex((current) => Math.min(current + 1, STEPS.length - 1));
      }
      if (event.key === "ArrowLeft") {
        setIndex((current) => Math.max(current - 1, 0));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, finish]);

  if (!open || !step) {
    return null;
  }

  const pad = 10;
  const spotlight = rect
    ? {
        top: Math.max(8, rect.top - pad),
        left: Math.max(8, rect.left - pad),
        width: rect.width + pad * 2,
        height: rect.height + pad * 2,
      }
    : null;

  return (
    <div className="pointer-events-none fixed inset-0 z-[60]" role="dialog" aria-modal="true" aria-labelledby="tour-title">
      <div className="pointer-events-none absolute inset-0 bg-canvas/70 backdrop-blur-[2px]" />
      {spotlight ? (
        <div
          className="pointer-events-none absolute rounded-2xl ring-2 ring-ai"
          style={{
            top: spotlight.top,
            left: spotlight.left,
            width: spotlight.width,
            height: spotlight.height,
            boxShadow: "0 0 0 9999px rgb(9 9 11 / 0.72)",
          }}
        />
      ) : null}
      <AnimatePresence mode="wait">
        <motion.div
          key={step.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 6 }}
          className="pointer-events-auto absolute bottom-6 right-6 z-[1] w-[min(100%-2rem,22rem)] rounded-2xl border border-ai/40 bg-surface p-4 shadow-[var(--shadow-card)]"
        >
          <p className="text-[10px] font-medium uppercase tracking-wide text-ai">
            Step {index + 1} of {STEPS.length}
          </p>
          <h2 id="tour-title" className="mt-1 text-sm font-semibold">
            {step.title}
          </h2>
          <p className="mt-1.5 text-xs leading-5 text-muted">{step.body}</p>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="rounded-lg border border-border px-2.5 py-1 text-xs text-muted hover:text-foreground"
              onClick={finish}
            >
              Skip Tour
            </button>
            <div className="ml-auto flex gap-2">
              <button
                type="button"
                className="rounded-lg border border-border px-2.5 py-1 text-xs disabled:opacity-40"
                disabled={index === 0}
                onClick={() => setIndex((current) => Math.max(0, current - 1))}
              >
                Previous
              </button>
              {last ? (
                <button
                  type="button"
                  className="rp-btn-ripple rounded-lg bg-ai px-2.5 py-1 text-xs font-medium text-canvas"
                  onClick={finish}
                >
                  Finish
                </button>
              ) : (
                <button
                  type="button"
                  className="rp-btn-ripple rounded-lg bg-ai px-2.5 py-1 text-xs font-medium text-canvas"
                  onClick={() => setIndex((current) => current + 1)}
                >
                  Next
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
