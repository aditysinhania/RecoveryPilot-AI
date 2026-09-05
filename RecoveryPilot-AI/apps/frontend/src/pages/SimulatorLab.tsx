import { GitCompare } from "lucide-react";
import { AIScenarioInsights } from "@/components/simulator/AIScenarioInsights";
import { ComparisonDrawer } from "@/components/simulator/ComparisonDrawer";
import { KPIComparisonGrid } from "@/components/simulator/KPIComparisonGrid";
import { SavedScenarioCard } from "@/components/simulator/SavedScenarioCard";
import { ScenarioImpactCharts } from "@/components/simulator/ScenarioImpactCharts";
import { ScenarioSummaryCard } from "@/components/simulator/ScenarioSummaryCard";
import { SimulatorControlPanel } from "@/components/simulator/SimulatorControlPanel";
import { EmptyState } from "@/components/shared/EmptyState";
import { DashboardSkeleton } from "@/components/shared/LoadingSkeleton";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { useSimulatorLab } from "@/hooks/useSimulatorLab";

/** Interactive simulator playground. Snapshot transforms only; no engine calls. */
export default function SimulatorLabPage() {
  const lab = useSimulatorLab();

  return (
    <div className="space-y-3" data-tour="simulator">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold tracking-tight">Simulator Lab</h1>
          <p className="text-[11px] text-muted">
            Change business conditions and replay RecoveryPilot against the selected baseline. Seed-42 FitLife is the
            source dataset — engines and Razorpay are never called.
            {lab.status.available ? ` Simulator seed ${lab.status.default_seed}.` : ""}
          </p>
        </div>
        <button
          type="button"
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border px-2.5 text-xs hover:bg-surface-hover"
          onClick={() => lab.setDrawerOpen(true)}
        >
          <GitCompare size={13} aria-hidden />
          Compare with seed 42
        </button>
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-[18rem_1fr]">
        <SimulatorControlPanel
          draft={lab.draft}
          dirty={lab.dirty}
          computing={lab.computing}
          onPatch={lab.patchDraft}
          onRun={lab.run}
          onReset={lab.resetSeed42}
          onSave={() => lab.persist()}
        />
        <div className="min-w-0 space-y-4">
          {lab.computing ? (
            <DashboardSkeleton />
          ) : (
            <>
              <ScenarioSummaryCard result={lab.result} />
              <SectionHeader
                title="Live KPI comparison"
                description="RecoveryPilot AI versus the selected baseline. Deltas are green when RecoveryPilot wins."
              />
              <KPIComparisonGrid key={lab.result.id} ai={lab.result.ai} baseline={lab.result.baseline} />
              <SectionHeader title="Scenario impact" description="Funnel, diagnosis, planner, segments, rails, and timeline." />
              <ScenarioImpactCharts key={`${lab.result.id}-charts`} current={lab.result} seed42={lab.seed42} />
              <AIScenarioInsights key={`${lab.result.id}-insights`} insights={lab.result.insights} />
              <section>
                <SectionHeader
                  title="Saved scenarios"
                  description="Stored in this browser only. Reload reapplies knobs; delete drops the row."
                />
                {lab.saved.length === 0 ? (
                  <EmptyState compact title="No saved scenarios" description="Run a simulation, then Save scenario." />
                ) : (
                  <div className="grid gap-2 md:grid-cols-2">
                    {lab.saved.map((row) => (
                      <SavedScenarioCard
                        key={row.id}
                        row={row}
                        onReload={lab.reloadSaved}
                        onDelete={lab.removeSaved}
                      />
                    ))}
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </div>

      <ComparisonDrawer
        open={lab.drawerOpen}
        current={lab.result}
        seed42={lab.seed42}
        onClose={() => lab.setDrawerOpen(false)}
      />
    </div>
  );
}
