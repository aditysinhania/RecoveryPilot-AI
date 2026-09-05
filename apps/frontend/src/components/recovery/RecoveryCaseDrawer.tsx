import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { AuditEventCard } from "@/components/recovery/AuditEventCard";
import { CaseHeader } from "@/components/recovery/CaseHeader";
import { DiagnosisCard } from "@/components/recovery/DiagnosisCard";
import { ExecutorCard } from "@/components/recovery/ExecutorCard";
import { GeminiExplanationCard } from "@/components/recovery/GeminiExplanationCard";
import { PlannerCard } from "@/components/recovery/PlannerCard";
import { PolicyCard } from "@/components/recovery/PolicyCard";
import { RecoveryTimeline } from "@/components/recovery/RecoveryTimeline";
import { EmptyState, ErrorState } from "@/components/shared/EmptyState";
import { fadeUp } from "@/lib/motion";
import type { CaseDrawerModel } from "@/types/recovery";

interface RecoveryCaseDrawerProps {
  open: boolean;
  model: CaseDrawerModel | undefined;
  loading: boolean;
  error: boolean;
  onClose: () => void;
  onRetry: () => void;
}

const FOCUSABLE =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

function DrawerSkeleton() {
  return (
    <div className="space-y-3 p-4" role="status" aria-label="Loading recovery case">
      <div className="flex gap-3">
        <div className="h-11 w-11 animate-pulse rounded-full bg-surface-hover" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-40 animate-pulse rounded bg-surface-hover" />
          <div className="h-3 w-28 animate-pulse rounded bg-surface-hover" />
          <div className="h-5 w-24 animate-pulse rounded bg-surface-hover" />
        </div>
      </div>
      {Array.from({ length: 5 }, (_, index) => (
        <div key={index} className="h-28 animate-pulse rounded-xl border border-border bg-surface" />
      ))}
    </div>
  );
}

/** Right-side read-only case inspector. Does not navigate away from the queue. */
export function RecoveryCaseDrawer({
  open,
  model,
  loading,
  error,
  onClose,
  onRetry,
}: RecoveryCaseDrawerProps) {
  const panelRef = useRef<HTMLElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const panel = panelRef.current;
    const first = panel?.querySelector<HTMLElement>(FOCUSABLE);
    first?.focus();

    const onKey = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panel) {
        return;
      }
      const nodes = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (node) => !node.hasAttribute("disabled"),
      );
      if (nodes.length === 0) {
        return;
      }
      const head = nodes[0];
      const tail = nodes[nodes.length - 1];
      if (event.shiftKey && document.activeElement === head) {
        event.preventDefault();
        tail.focus();
      } else if (!event.shiftKey && document.activeElement === tail) {
        event.preventDefault();
        head.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    const original = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = original;
      previousFocus.current?.focus();
    };
  }, [open, onClose, loading, model]);

  return (
    <AnimatePresence>
      {open ? (
        <>
          <motion.button
            type="button"
            aria-label="Close case drawer"
            className="fixed inset-0 z-40 bg-black/55"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />
          <motion.aside
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="case-drawer-title"
            className="fixed inset-y-0 right-0 z-50 flex w-full max-w-full flex-col border-l border-border bg-canvas-muted shadow-[var(--shadow-card)] sm:max-w-[480px]"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.2, ease: "easeOut" }}
          >
            <div className="flex items-center justify-between border-b border-border px-4 py-2">
              <p className="text-xs font-medium uppercase tracking-wide text-muted">Recovery case</p>
              <button
                type="button"
                onClick={onClose}
                className="rounded-lg p-1.5 text-muted hover:bg-surface-hover hover:text-foreground"
                aria-label="Close drawer"
              >
                <X size={16} />
              </button>
            </div>
            <div className="rp-scroll min-h-0 flex-1 overflow-y-auto">
              {loading && !model ? (
                <DrawerSkeleton />
              ) : error && !model ? (
                <div className="p-4">
                  <ErrorState message="Could not load this recovery case." onRetry={onRetry} />
                </div>
              ) : model ? (
                <>
                  <CaseHeader detail={model.case} />
                  <motion.div className="space-y-3 p-3 sm:p-4" {...fadeUp}>
                    <DiagnosisCard diagnosis={model.diagnosis} />
                    <PolicyCard policy={model.policy} />
                    <PlannerCard planner={model.planner} />
                    <ExecutorCard
                      execution={model.execution}
                      recoveryCaseId={model.case.recovery_case_id}
                      timeline={model.timeline}
                      audit={model.audit}
                    />
                    <GeminiExplanationCard
                      merchant={model.explanations.merchant}
                      customer={model.explanations.customer}
                      compliance={model.explanations.compliance}
                    />
                    <RecoveryTimeline events={model.timeline} />
                    <section aria-labelledby="audit-heading">
                      <h3 id="audit-heading" className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
                        Audit Trail
                      </h3>
                      <div className="space-y-2">
                        {model.audit.length === 0 ? (
                          <EmptyState
                            compact
                            title="No audit events"
                            description="This case has no recorded audit trail yet."
                          />
                        ) : (
                          model.audit.map((event, index) => (
                            <AuditEventCard key={event.event_id ?? `${event.timestamp}-${index}`} event={event} />
                          ))
                        )}
                      </div>
                    </section>
                  </motion.div>
                </>
              ) : (
                <div className="p-4">
                  <EmptyState
                    title="Case not found"
                    description="This recovery case is not in the live queue or the FitLife snapshot."
                  />
                </div>
              )}
            </div>
          </motion.aside>
        </>
      ) : null}
    </AnimatePresence>
  );
}
