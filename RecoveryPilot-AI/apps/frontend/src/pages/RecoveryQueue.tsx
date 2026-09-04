import { useEffect, useState, type ReactNode } from "react";
import { useOutletContext, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  Ban,
  CircleDollarSign,
  FolderOpen,
  Hourglass,
  Wallet,
} from "lucide-react";
import { RecoveryCaseDrawer } from "@/components/recovery/RecoveryCaseDrawer";
import { RecoveryFilters } from "@/components/recovery/RecoveryFilters";
import { RecoveryQueueTable } from "@/components/recovery/RecoveryQueueTable";
import { ErrorState } from "@/components/shared/EmptyState";
import { useMerchantDashboard } from "@/hooks/useMerchantDashboard";
import { useRecoveryCase } from "@/hooks/useRecoveryCase";
import { useRecoveryQueue } from "@/hooks/useRecoveryQueue";
import { formatCompact, formatPaise } from "@/lib/format";
import { EMPTY_FILTERS } from "@/lib/recoveryMap";
import { emptyQueuePage } from "@/services/recoveryQueue";
import type { QueueSortKey, RecoveryQueueFilters } from "@/types/recovery";

type LayoutContext = ReturnType<typeof useMerchantDashboard>;

const PAGE_SIZE = 25;

function SecondaryChip({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: string;
  tone: string;
  icon: ReactNode;
}) {
  return (
    <div className="flex min-w-[108px] items-center gap-2 rounded-lg border border-border bg-surface px-2.5 py-1.5">
      <span className={tone} aria-hidden>
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-wide text-muted">{label}</p>
        <p className={`text-sm font-semibold tabular-nums ${tone}`}>{value}</p>
      </div>
    </div>
  );
}

/** Merchant recovery operations queue. Read-only in Phase 8B. */
export default function RecoveryQueue() {
  const { merchantId, merchants, setMerchantId } = useOutletContext<LayoutContext>();
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState<RecoveryQueueFilters>({
    ...EMPTY_FILTERS,
    merchantId,
  });
  const [page, setPage] = useState(1);
  const [sortKey, setSortKey] = useState<QueueSortKey>("priority_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const selectedId = searchParams.get("case");

  useEffect(() => {
    setFilters((current) =>
      current.merchantId === merchantId ? current : { ...current, merchantId },
    );
  }, [merchantId]);

  const queueQuery = useRecoveryQueue({
    merchantId: filters.merchantId || merchantId,
    filters,
    page,
    pageSize: PAGE_SIZE,
    sortKey,
    sortDir,
  });
  const caseQuery = useRecoveryCase(selectedId);

  const pageData = queueQuery.data?.page ?? emptyQueuePage(PAGE_SIZE);
  const summary = queueQuery.data?.summary;

  const onFilters = (next: RecoveryQueueFilters): void => {
    setFilters(next);
    setPage(1);
    if (next.merchantId && next.merchantId !== merchantId) {
      setMerchantId(next.merchantId);
    }
  };

  const onSort = (key: QueueSortKey): void => {
    if (key === sortKey) {
      setSortDir((current) => (current === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "customer_name" || key === "plan_name" ? "asc" : "desc");
    }
    setPage(1);
  };

  const openCase = (id: string): void => {
    const next = new URLSearchParams(searchParams);
    next.set("case", id);
    setSearchParams(next, { replace: true });
  };

  const closeCase = (): void => {
    const next = new URLSearchParams(searchParams);
    next.delete("case");
    setSearchParams(next, { replace: true });
  };

  const waiting = summary ? summary.waiting_retry + summary.waiting_promise : 0;

  return (
    <div className="flex h-[calc(100vh-5.25rem)] min-h-0 min-w-0 w-full flex-col gap-2 overflow-hidden">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h1 className="text-base font-semibold tracking-tight">Recovery Queue</h1>
          <p className="text-[11px] text-muted">Inspect AI decisions for every failed payment. Read-only.</p>
        </div>
      </div>
      {queueQuery.data?.source === "simulator" && !queueQuery.isPending ? (
        <ErrorState
          compact
          message="Live queue APIs are unavailable. Showing the FitLife seed-42 simulator snapshot."
          onRetry={() => {
            void queueQuery.refetch();
          }}
        />
      ) : null}
      <RecoveryFilters filters={filters} merchants={merchants} onChange={onFilters} />
      <div className="flex min-w-0 flex-wrap items-stretch gap-1.5">
        {!summary ? (
          Array.from({ length: 6 }, (_, index) => (
            <div key={index} className="h-12 w-32 animate-pulse rounded-lg bg-surface" />
          ))
        ) : (
          <>
            <div className="flex min-w-[220px] items-center gap-3 rounded-xl border border-info/30 bg-info-muted/50 px-3 py-1.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-info-muted text-info" aria-hidden>
                <CircleDollarSign size={16} />
              </span>
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted">Revenue at risk</p>
                <p className="text-lg font-semibold tabular-nums leading-tight text-info">
                  {formatPaise(summary.total_revenue_at_risk)}
                </p>
              </div>
            </div>
            <SecondaryChip
              label="Open cases"
              value={formatCompact(summary.open_cases)}
              tone="text-waiting"
              icon={<FolderOpen size={13} />}
            />
            <SecondaryChip
              label="Waiting"
              value={formatCompact(waiting)}
              tone="text-waiting"
              icon={<Hourglass size={13} />}
            />
            <SecondaryChip
              label="Escalated"
              value={formatCompact(summary.escalated_cases)}
              tone="text-blocked"
              icon={<AlertTriangle size={13} />}
            />
            <SecondaryChip
              label="Stopped"
              value={formatCompact(summary.stopped_cases)}
              tone="text-zinc-400"
              icon={<Ban size={13} />}
            />
            <SecondaryChip
              label="Recovered today"
              value={formatCompact(summary.recovered_today)}
              tone="text-recovered"
              icon={<Wallet size={13} />}
            />
          </>
        )}
      </div>
      <RecoveryQueueTable
        rows={pageData.items}
        selectedId={selectedId}
        sortKey={sortKey}
        sortDir={sortDir}
        loading={queueQuery.isPending}
        page={pageData.page}
        pageSize={pageData.page_size}
        total={pageData.total}
        totalPages={pageData.total_pages}
        hasNext={pageData.has_next}
        hasPrevious={pageData.has_previous}
        onSort={onSort}
        onOpen={openCase}
        onPage={setPage}
      />
      <RecoveryCaseDrawer
        open={Boolean(selectedId)}
        model={caseQuery.data}
        loading={caseQuery.isPending}
        error={caseQuery.isError}
        onClose={closeCase}
        onRetry={() => {
          void caseQuery.refetch();
        }}
      />
    </div>
  );
}
