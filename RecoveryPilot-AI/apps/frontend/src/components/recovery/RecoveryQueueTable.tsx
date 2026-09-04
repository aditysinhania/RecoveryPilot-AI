import { useEffect, useMemo, useRef, useState, type MouseEvent, type UIEvent } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { PriorityBadge } from "@/components/shared/PriorityBadge";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatPaise, formatPercent, formatRelativeTime, titleCase } from "@/lib/format";
import { contributorsFor, recoveryProbability } from "@/lib/recoveryMap";
import type { QueueRow, QueueSortKey } from "@/types/recovery";

const ROW_HEIGHT = 48;
const TABLE_MIN_WIDTH = 1120;

const COLUMNS: { key: QueueSortKey; label: string; width: string }[] = [
  { key: "customer_name", label: "Customer", width: "14%" },
  { key: "plan_name", label: "Plan", width: "9%" },
  { key: "amount", label: "Amount", width: "8%" },
  { key: "diagnosed_reason", label: "Diagnosis", width: "12%" },
  { key: "planner_strategy", label: "Planner Strategy", width: "13%" },
  { key: "policy_status", label: "Policy", width: "8%" },
  { key: "recovery_status", label: "Recovery Status", width: "12%" },
  { key: "priority_score", label: "Priority", width: "7%" },
  { key: "last_updated", label: "Updated", width: "7%" },
  { key: "ai_confidence", label: "AI Confidence", width: "10%" },
];

interface RecoveryQueueTableProps {
  rows: QueueRow[];
  selectedId: string | null;
  sortKey: QueueSortKey;
  sortDir: "asc" | "desc";
  loading: boolean;
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  onSort: (key: QueueSortKey) => void;
  onOpen: (id: string) => void;
  onPage: (page: number) => void;
}

function confidenceBand(score: number): { label: string; bar: string; badge: string } {
  if (score >= 0.75) {
    return { label: "High", bar: "bg-recovered", badge: "bg-recovered-muted text-recovered" };
  }
  if (score >= 0.5) {
    return { label: "Medium", bar: "bg-waiting", badge: "bg-waiting-muted text-waiting" };
  }
  return { label: "Low", bar: "bg-blocked", badge: "bg-blocked-muted text-blocked" };
}

function CellText({ value, className = "" }: { value: string; className?: string }) {
  return (
    <span className={`block truncate ${className}`} title={value}>
      {value}
    </span>
  );
}

function ConfidenceCell({ row }: { row: QueueRow }) {
  const value = row.ai_confidence ?? 0;
  const pct = Math.round(value * 100);
  const band = confidenceBand(value);
  const contributors = contributorsFor(row.diagnosed_reason ?? row.failure_reason);
  const tooltip = [`${pct}% · ${band.label}`, ...contributors.map((item) => `${item.label} ${Math.round(item.weight * 100)}%`)].join(
    " · ",
  );
  return (
    <div className="min-w-0 pr-1" title={tooltip}>
      <div className="flex items-center gap-1.5">
        <div className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-zinc-800" aria-hidden>
          <div className={`h-full rounded-full ${band.bar}`} style={{ width: `${pct}%` }} />
        </div>
        <span className={`shrink-0 rounded-full px-1.5 py-px text-[10px] font-medium ${band.badge}`}>{band.label}</span>
      </div>
      <p className="mt-0.5 text-[10px] tabular-nums text-muted">{formatPercent(value, 0)}</p>
    </div>
  );
}

function SortIcon({ active, dir }: { active: boolean; dir: "asc" | "desc" }) {
  if (!active) {
    return <ArrowUpDown size={11} className="text-zinc-600" aria-hidden />;
  }
  return dir === "asc" ? <ArrowUp size={11} aria-hidden /> : <ArrowDown size={11} aria-hidden />;
}

function expectedRecovered(row: QueueRow): number {
  const probability = recoveryProbability(
    row.customer_segment,
    row.diagnosed_reason ?? row.failure_reason,
    row.recovery_status,
  );
  return Math.round(row.amount * probability);
}

interface PreviewState {
  row: QueueRow;
  x: number;
  y: number;
  place: "above" | "below";
}

function AiPreview({ preview }: { preview: PreviewState }) {
  const { row, x, y, place } = preview;
  const confidence = row.ai_confidence ?? 0;
  const band = confidenceBand(confidence);
  const diagnosis = titleCase(row.diagnosed_reason ?? row.failure_reason ?? "Unknown");
  return (
    <motion.div
      role="tooltip"
      initial={{ opacity: 0, y: place === "below" ? 4 : -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: place === "below" ? 4 : -4 }}
      transition={{ duration: 0.15 }}
      className="pointer-events-none fixed z-50 w-72 rounded-xl border border-border-strong bg-surface-raised p-3 shadow-[var(--shadow-card)]"
      style={{
        left: Math.min(x, window.innerWidth - 300),
        top: place === "below" ? y : undefined,
        bottom: place === "above" ? window.innerHeight - y : undefined,
      }}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wide text-ai">AI preview</p>
      <p className="mt-1 truncate text-sm font-medium text-foreground">{row.customer_name}</p>
      <dl className="mt-2 space-y-1 text-[11px]">
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Diagnosis</dt>
          <dd className="truncate font-medium text-foreground" title={diagnosis}>
            {diagnosis}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Planner</dt>
          <dd className="truncate font-medium text-foreground" title={titleCase(row.planner_strategy)}>
            {titleCase(row.planner_strategy)}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Confidence</dt>
          <dd className={`font-medium ${band.badge.includes("recovered") ? "text-recovered" : band.badge.includes("waiting") ? "text-waiting" : "text-blocked"}`}>
            {formatPercent(confidence, 0)} · {band.label}
          </dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted">Expected recovered</dt>
          <dd className="font-medium tabular-nums text-recovered">{formatPaise(expectedRecovered(row))}</dd>
        </div>
      </dl>
    </motion.div>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-1.5 p-3" role="status" aria-label="Loading recovery queue">
      {Array.from({ length: 10 }, (_, index) => (
        <div key={index} className="h-10 animate-pulse rounded-md bg-surface-hover" />
      ))}
    </div>
  );
}

/** Windowed recovery-queue table. Header and rows share table-fixed column widths. */
export function RecoveryQueueTable({
  rows,
  selectedId,
  sortKey,
  sortDir,
  loading,
  page,
  pageSize,
  total,
  totalPages,
  hasNext,
  hasPrevious,
  onSort,
  onOpen,
  onPage,
}: RecoveryQueueTableProps) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const previewTimer = useRef<number | null>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [viewport, setViewport] = useState(420);
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const start = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - 4);
  const visible = Math.ceil(viewport / ROW_HEIGHT) + 8;

  useEffect(() => {
    const element = scrollerRef.current;
    if (!element) {
      return;
    }
    const sync = (): void => {
      setViewport(element.clientHeight || 420);
    };
    sync();
    const observer = new ResizeObserver(sync);
    observer.observe(element);
    return () => {
      observer.disconnect();
      if (previewTimer.current) {
        window.clearTimeout(previewTimer.current);
      }
    };
  }, [rows.length, loading]);
  const slice = useMemo(() => rows.slice(start, start + visible), [rows, start, visible]);
  const endPad = Math.max(0, rows.length - start - slice.length);

  const hidePreview = (): void => {
    if (previewTimer.current) {
      window.clearTimeout(previewTimer.current);
      previewTimer.current = null;
    }
    setPreview(null);
  };

  const onScroll = (event: UIEvent<HTMLDivElement>): void => {
    setScrollTop(event.currentTarget.scrollTop);
    hidePreview();
  };

  const showPreview = (row: QueueRow, event: MouseEvent<HTMLTableRowElement>): void => {
    const rect = event.currentTarget.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const place: "above" | "below" = spaceBelow < 150 ? "above" : "below";
    const next: PreviewState = {
      row,
      x: Math.min(rect.left + 24, window.innerWidth - 300),
      y: place === "below" ? rect.bottom + 6 : rect.top - 6,
      place,
    };
    if (previewTimer.current) {
      window.clearTimeout(previewTimer.current);
    }
    previewTimer.current = window.setTimeout(() => {
      setPreview(next);
    }, 140);
  };

  return (
    <section className="flex min-h-0 min-w-0 w-full flex-1 flex-col overflow-hidden rounded-xl border border-border bg-surface">
      {loading && rows.length === 0 ? (
        <TableSkeleton />
      ) : rows.length === 0 ? (
        <div className="p-5">
          <EmptyState
            title="No recovery cases match"
            description="Clear filters or wait for the next failed payment to land in the queue."
          />
        </div>
      ) : (
        <div
          ref={scrollerRef}
          className="rp-scroll min-h-0 flex-1 overflow-auto"
          onScroll={onScroll}
          role="region"
          aria-label="Recovery queue"
        >
          <table className="w-full table-fixed border-collapse" style={{ minWidth: TABLE_MIN_WIDTH }}>
            <colgroup>
              {COLUMNS.map((column) => (
                <col key={column.key} style={{ width: column.width }} />
              ))}
            </colgroup>
            <thead className="sticky top-0 z-20">
              <tr className="border-b border-border bg-canvas-muted text-[11px] font-medium uppercase tracking-wide text-muted">
                {COLUMNS.map((column) => (
                  <th key={column.key} className="overflow-hidden px-2 py-2 text-left font-medium">
                    <button
                      type="button"
                      className="inline-flex max-w-full items-center gap-1 hover:text-foreground"
                      onClick={() => onSort(column.key)}
                      aria-sort={sortKey === column.key ? (sortDir === "asc" ? "ascending" : "descending") : "none"}
                    >
                      <span className="truncate">{column.label}</span>
                      <SortIcon active={sortKey === column.key} dir={sortDir} />
                    </button>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {start > 0 ? (
                <tr aria-hidden>
                  <td colSpan={COLUMNS.length} style={{ height: start * ROW_HEIGHT, padding: 0, border: 0 }} />
                </tr>
              ) : null}
              {slice.map((row) => {
                const selected = row.recovery_case_id === selectedId;
                const diagnosis = titleCase(row.diagnosed_reason ?? row.failure_reason ?? "Unknown");
                return (
                  <tr
                    key={row.recovery_case_id}
                    tabIndex={0}
                    aria-selected={selected}
                    className={`cursor-pointer border-b border-border/80 transition-[background,box-shadow] duration-150 hover:z-10 hover:bg-surface-hover hover:shadow-[0_0_0_1px_var(--color-border-strong),0_8px_20px_rgb(0_0_0/0.35)] focus-visible:bg-surface-hover ${
                      selected ? "bg-surface-hover shadow-[inset_2px_0_0_var(--color-info)]" : ""
                    }`}
                    style={{ height: ROW_HEIGHT }}
                    onClick={() => {
                      hidePreview();
                      onOpen(row.recovery_case_id);
                    }}
                    onMouseEnter={(event) => showPreview(row, event)}
                    onMouseLeave={hidePreview}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        onOpen(row.recovery_case_id);
                      }
                    }}
                  >
                    <td className="overflow-hidden px-2 py-1.5 align-middle">
                      <CellText value={row.customer_name} className="font-medium text-foreground" />
                      <CellText value={titleCase(row.customer_segment)} className="text-[11px] text-muted" />
                    </td>
                    <td className="overflow-hidden px-2 py-1.5 align-middle text-muted">
                      <CellText value={row.plan_name} />
                    </td>
                    <td className="overflow-hidden px-2 py-1.5 align-middle font-medium tabular-nums">
                      <CellText value={formatPaise(row.amount)} />
                    </td>
                    <td className="overflow-hidden px-2 py-1.5 align-middle text-muted">
                      <CellText value={diagnosis} />
                    </td>
                    <td className="overflow-hidden px-2 py-1.5 align-middle text-muted">
                      <CellText value={titleCase(row.planner_strategy)} />
                    </td>
                    <td className="overflow-hidden px-2 py-1.5 align-middle">
                      <StatusBadge status={row.policy_status} />
                    </td>
                    <td className="overflow-hidden px-2 py-1.5 align-middle">
                      <StatusBadge status={row.recovery_status} />
                    </td>
                    <td className="overflow-hidden px-2 py-1.5 align-middle">
                      <PriorityBadge score={row.priority_score ?? 0} />
                    </td>
                    <td className="overflow-hidden px-2 py-1.5 align-middle text-xs text-muted">
                      <time className="block truncate" dateTime={row.last_updated} title={row.last_updated}>
                        {formatRelativeTime(row.last_updated)}
                      </time>
                    </td>
                    <td className="overflow-hidden px-2 py-1.5 align-middle">
                      <ConfidenceCell row={row} />
                    </td>
                  </tr>
                );
              })}
              {endPad > 0 ? (
                <tr aria-hidden>
                  <td colSpan={COLUMNS.length} style={{ height: endPad * ROW_HEIGHT, padding: 0, border: 0 }} />
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      )}
      <AnimatePresence>{preview ? <AiPreview preview={preview} /> : null}</AnimatePresence>
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-border px-3 py-1.5 text-xs text-muted">
        <p>
          {total === 0
            ? "0 cases"
            : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}`}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="rounded-md border border-border px-2 py-0.5 disabled:opacity-40"
            disabled={!hasPrevious}
            onClick={() => onPage(page - 1)}
          >
            Previous
          </button>
          <span>
            Page {page} / {totalPages}
          </span>
          <button
            type="button"
            className="rounded-md border border-border px-2 py-0.5 disabled:opacity-40"
            disabled={!hasNext}
            onClick={() => onPage(page + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
