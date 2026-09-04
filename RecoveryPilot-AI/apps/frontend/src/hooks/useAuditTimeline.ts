import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { EMPTY_AUDIT_FILTERS } from "@/lib/auditMap";
import {
  fetchAuditKpis,
  fetchAuditPage,
  fetchCorrelationReplay,
  insightsFromPage,
} from "@/services/audit";
import type { AuditFilters } from "@/types/audit";

/** Explorer state: filters, page, KPI strip, and optional correlation replay. */
export function useAuditTimeline(initial: Partial<AuditFilters> = {}) {
  const [filters, setFilters] = useState<AuditFilters>({ ...EMPTY_AUDIT_FILTERS, ...initial });
  const [page, setPage] = useState(1);
  const [inspectId, setInspectId] = useState(initial.correlationId?.trim() ?? "");

  const eventsQuery = useQuery({
    queryKey: ["audit-events", filters, page],
    queryFn: () => fetchAuditPage(filters, page),
    staleTime: 20_000,
    retry: 0,
    placeholderData: (previous) => previous,
  });

  const kpisQuery = useQuery({
    queryKey: ["audit-kpis"],
    queryFn: fetchAuditKpis,
    staleTime: 60_000,
    retry: 0,
  });

  const replayId = inspectId.trim();
  const replayQuery = useQuery({
    queryKey: ["audit-correlation", replayId],
    queryFn: () => fetchCorrelationReplay(replayId),
    enabled: replayId.length > 0,
    staleTime: 30_000,
    retry: 0,
  });

  const pageData = eventsQuery.data;
  const insights = useMemo(() => (pageData ? insightsFromPage(pageData) : null), [pageData]);

  const patchFilters = (next: AuditFilters): void => {
    setFilters(next);
    setPage(1);
  };

  return {
    filters,
    setFilters: patchFilters,
    page,
    setPage,
    inspectId,
    setInspectId,
    events: pageData,
    kpis: kpisQuery.data?.kpis ?? null,
    kpiSource: kpisQuery.data?.source ?? "simulator",
    insights,
    replay: replayQuery.data ?? null,
    isLoading: eventsQuery.isPending && !eventsQuery.data,
    isError: Boolean(eventsQuery.isError && eventsQuery.data?.source !== "live"),
    isFetching: eventsQuery.isFetching || kpisQuery.isFetching,
    replayLoading: replayQuery.isFetching,
    replayError: replayQuery.isError && !replayQuery.data,
    refetch: (): void => {
      void eventsQuery.refetch();
      void kpisQuery.refetch();
      if (replayId) {
        void replayQuery.refetch();
      }
    },
  };
}
