import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { ScenarioDeltaCard } from "@/components/simulator/ScenarioDeltaCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { fadeUp } from "@/lib/motion";
import { baselineLabel, conditionChips, scenarioDeltas } from "@/lib/simulatorLab";
import type { ScenarioResult } from "@/types/simulatorLab";

interface ComparisonDrawerProps {
  open: boolean;
  current: ScenarioResult;
  seed42: ScenarioResult;
  onClose: () => void;
}

const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/** Compare the current run with the FitLife seed-42 snapshot. */
export function ComparisonDrawer({ open, current, seed42, onClose }: ComparisonDrawerProps) {
  const panelRef = useRef<HTMLElement>(null);
  const deltas = scenarioDeltas(current, seed42);
  const currentChips = conditionChips(current.controls).filter((chip) => chip.active);
  const seedChips = conditionChips(seed42.controls).filter((chip) => chip.active);
  const strategyShift = current.strategies
    .map((row) => {
      const prior = seed42.strategies.find((item) => item.key === row.key);
      return {
        label: row.label,
        current: row.recovered,
        seed: prior?.recovered ?? 0,
      };
    })
    .filter((row) => row.current !== row.seed);

  useEffect(() => {
    if (!open) {
      return;
    }
    const panel = panelRef.current;
    const first = panel?.querySelector<HTMLElement>(FOCUSABLE);
    first?.focus();
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-40 flex justify-end bg-black/50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.aside
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="compare-title"
            className="flex h-full w-full max-w-md flex-col border-l border-border bg-canvas-muted shadow-[var(--shadow-card)]"
            {...fadeUp}
            onClick={(event) => event.stopPropagation()}
          >
            <header className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
              <h2 id="compare-title" className="text-sm font-semibold">
                Scenario comparison
              </h2>
              <button
                type="button"
                className="rounded-md border border-border p-1.5 hover:bg-surface-hover"
                onClick={onClose}
                aria-label="Close comparison"
              >
                <X size={14} />
              </button>
            </header>
            <div className="rp-scroll flex-1 space-y-4 overflow-y-auto p-4">
              <section>
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted">Current</h3>
                <p className="mt-1 text-xs text-foreground">{current.label}</p>
                <p className="text-[11px] text-muted">{baselineLabel(current.controls.baselineStrategy)}</p>
                <ul className="mt-2 flex flex-wrap gap-1">
                  {currentChips.map((chip) => (
                    <li key={chip.label} className="rounded-full bg-ai-muted px-2 py-0.5 text-[10px] text-ai">
                      {chip.label}
                    </li>
                  ))}
                </ul>
              </section>
              <section>
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted">Seed 42 default</h3>
                <p className="mt-1 text-xs text-foreground">{seed42.label}</p>
                <ul className="mt-2 flex flex-wrap gap-1">
                  {seedChips.map((chip) => (
                    <li key={chip.label} className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-muted">
                      {chip.label}
                    </li>
                  ))}
                </ul>
              </section>
              <section className="space-y-2">
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted">Metric deltas</h3>
                {deltas.map((row) => (
                  <ScenarioDeltaCard key={row.key} row={row} leftLabel="Current" rightLabel="Seed 42" />
                ))}
              </section>
              <section>
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted">Changed strategies</h3>
                {strategyShift.length === 0 ? (
                  <EmptyState compact title="Same planner mix" description="Recovered case counts match seed 42." />
                ) : (
                  <ul className="mt-2 space-y-1.5 text-xs">
                    {strategyShift.map((row) => (
                      <li key={row.label} className="flex justify-between rounded-lg border border-border px-2.5 py-1.5">
                        <span>{row.label}</span>
                        <span className="tabular-nums text-muted">
                          {row.seed} → {row.current}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>
          </motion.aside>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
