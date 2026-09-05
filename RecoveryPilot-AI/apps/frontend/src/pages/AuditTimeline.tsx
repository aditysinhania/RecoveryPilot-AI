import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { GitBranch } from "lucide-react";
import { AuditExportButtons } from "@/components/audit/AuditExportPanel";
import { AuditFilters } from "@/components/audit/AuditFilters";
import { AuditInspector } from "@/components/audit/AuditInspector";
import { AuditMetricsHeader } from "@/components/audit/AuditMetricsHeader";
import { ComplianceInsightsCard } from "@/components/audit/ComplianceInsightsCard";
import { CorrelationGroupCard } from "@/components/audit/CorrelationGroupCard";
import { EmptyState, ErrorState } from "@/components/shared/EmptyState";
import { TimelineSkeleton } from "@/components/shared/LoadingSkeleton";
import { EmptyWorkspace } from "@/components/workspace/EmptyWorkspace";
import { useAuditTimeline } from "@/hooks/useAuditTimeline";
import { useMerchantDashboard } from "@/hooks/useMerchantDashboard";
import { eventKey, groupByCorrelation } from "@/lib/auditMap";
import { FITLIFE_LIST_ID } from "@/services/dashboard";
import type { AuditEventView, AuditFilters as AuditFilterState } from "@/types/audit";
import { useOutletContext } from "react-router-dom";

type LayoutContext = ReturnType<typeof useMerchantDashboard>;

/** Compliance-grade audit explorer. Read-only. Existing /audit APIs only. */
export default function AuditTimelinePage() {
  const { emptyWorkspace, setMerchantId, isDemo } = useOutletContext<LayoutContext>();
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    filters,
    setFilters,
    page,
    setPage,
    inspectId,
    setInspectId,
    events,
    kpis,
    insights,
    replay,
    isLoading,
    isFetching,
    replayLoading,
    refetch,
  } = useAuditTimeline(
    {
      correlationId: searchParams.get("correlation") ?? "",
      caseId: searchParams.get("case") ?? "",
    },
    { enabled: !emptyWorkspace },
  );
  const [selected, setSelected] = useState<AuditEventView | null>(null);

  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (inspectId.trim()) {
      next.set("correlation", inspectId.trim());
    } else if (filters.correlationId.trim()) {
      next.set("correlation", filters.correlationId.trim());
    } else {
      next.delete("correlation");
    }
    if (filters.caseId.trim()) {
      next.set("case", filters.caseId.trim());
    } else {
      next.delete("case");
    }
    if (next.toString() !== searchParams.toString()) {
      setSearchParams(next, { replace: true });
    }
  }, [filters.caseId, filters.correlationId, inspectId, searchParams, setSearchParams]);

  const groups = useMemo(() => groupByCorrelation(events?.items ?? []), [events?.items]);

  const onSelect = (event: AuditEventView): void => {
    setSelected(event);
    setInspectId(event.correlation_id);
  };

  const onReplay = (): void => {
    const token = filters.correlationId.trim() || selected?.correlation_id || groups[0]?.correlation_id || "";
    if (!token) {
      return;
    }
    setInspectId(token);
    const match =
      selected?.correlation_id === token
        ? selected
        : groups.find((group) => group.correlation_id === token)?.latest ?? null;
    if (match) {
      setSelected(match);
    }
  };

  if (emptyWorkspace) {
    return <EmptyWorkspace onImportDemo={() => setMerchantId(FITLIFE_LIST_ID)} />;
  }

  if (isLoading) {
    return <TimelineSkeleton />;
  }

  const snapshot = events?.source === "simulator" && !isDemo;
  const selectedKey = selected ? eventKey(selected) : null;
  const replayTarget = filters.correlationId.trim() || selected?.correlation_id || "";

  return (
    <div className="space-y-3" data-tour="audit">
      <div>
        <h1 className="text-base font-semibold tracking-tight">Audit Timeline</h1>
        <p className="text-[11px] text-muted">
          Replay every recovery decision. Grouped by correlation.
          {events
            ? ` ${groups.length} workflows · ${events.items.length} of ${events.total.toLocaleString("en-IN")} events.`
            : ""}
        </p>
      </div>
      {isFetching ? (
        <p className="text-xs text-muted" aria-live="polite">
          Refreshing live APIs…
        </p>
      ) : null}
      {snapshot ? (
        <ErrorState
          compact
          message="Live audit APIs are unavailable. Showing the FitLife seed-42 simulator snapshot."
          onRetry={() => refetch()}
        />
      ) : null}

      {kpis ? <AuditMetricsHeader kpis={kpis} /> : null}
      {insights ? <ComplianceInsightsCard insights={insights} /> : null}

      <AuditFilters
        filters={filters}
        onChange={(next: AuditFilterState) => setFilters(next)}
        actions={
          <>
            <AuditExportButtons events={events?.items ?? []} />
            <button
              type="button"
              className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs text-foreground hover:bg-surface-hover disabled:opacity-40"
              disabled={!replayTarget && groups.length === 0}
              onClick={onReplay}
            >
              <GitBranch size={13} aria-hidden />
              Replay
            </button>
          </>
        }
      />

      <div className="grid items-start gap-4 lg:grid-cols-[3fr_2fr]">
        <section aria-label="Timeline explorer" className="min-w-0 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-semibold">Workflows</h2>
            {events && events.total_pages > 1 ? (
              <div className="flex items-center gap-2 text-xs text-muted">
                <button
                  type="button"
                  className="rounded-md border border-border px-2 py-1 disabled:opacity-40"
                  disabled={!events.has_previous}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </button>
                <span>
                  {events.page} / {events.total_pages}
                </span>
                <button
                  type="button"
                  className="rounded-md border border-border px-2 py-1 disabled:opacity-40"
                  disabled={!events.has_next}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </button>
              </div>
            ) : null}
          </div>
          {groups.length === 0 ? (
            <EmptyState title="No audit events" description="No rows match these filters in this window." />
          ) : (
            groups.map((group, index) => (
              <CorrelationGroupCard
                key={group.correlation_id}
                group={group}
                selectedKey={selectedKey}
                defaultOpen={index === 0 || group.correlation_id === inspectId}
                onSelect={onSelect}
              />
            ))
          )}
        </section>
        <div className="lg:sticky lg:top-[9.25rem] lg:max-h-[calc(100vh-10.5rem)] lg:overflow-y-auto rp-scroll">
          <AuditInspector
            event={selected}
            replay={replay}
            replayLoading={replayLoading}
            insights={insights}
          />
        </div>
      </div>
    </div>
  );
}
