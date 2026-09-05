interface LoadingSkeletonProps {
  className?: string;
  lines?: number;
}

/** Pulse placeholder for dashboard cards. */
export function LoadingSkeleton({ className = "", lines = 3 }: LoadingSkeletonProps) {
  return (
    <div className={`animate-pulse rounded-xl border border-border bg-surface p-5 ${className}`} aria-hidden>
      <div className="h-3 w-24 rounded bg-surface-hover" />
      <div className="mt-4 space-y-2">
        {Array.from({ length: lines }, (_, index) => (
          <div key={index} className="h-3 rounded bg-surface-hover" style={{ width: `${80 - index * 12}%` }} />
        ))}
      </div>
    </div>
  );
}

/** Full dashboard loading layout. */
export function DashboardSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading dashboard">
      <KpiSkeleton />
      <LoadingSkeleton lines={3} className="h-28" />
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    </div>
  );
}

/** Pulse placeholders for the KPI strip. */
export function KpiSkeleton() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6" role="status" aria-label="Loading metrics">
      {Array.from({ length: 6 }, (_, index) => (
        <LoadingSkeleton key={index} lines={2} />
      ))}
    </div>
  );
}

/** Pulse placeholder for a chart card. */
export function ChartSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-border bg-surface p-4" role="status" aria-label="Loading chart">
      <div className="h-3 w-32 rounded bg-surface-hover" />
      <div className="mt-4 h-40 rounded-lg bg-surface-hover" />
    </div>
  );
}

/** Pulse placeholder for queue and settings tables. */
export function TableSkeleton() {
  return (
    <div className="animate-pulse overflow-hidden rounded-xl border border-border" role="status" aria-label="Loading table">
      <div className="h-9 bg-surface-hover/60" />
      {Array.from({ length: 8 }, (_, index) => (
        <div key={index} className="flex gap-3 border-t border-border px-3 py-2.5">
          <div className="h-3 w-1/4 rounded bg-surface-hover" />
          <div className="h-3 w-1/5 rounded bg-surface-hover" />
          <div className="h-3 flex-1 rounded bg-surface-hover" />
        </div>
      ))}
    </div>
  );
}

/** Pulse placeholder for the audit timeline. */
export function TimelineSkeleton() {
  return (
    <div className="space-y-3" role="status" aria-label="Loading timeline">
      <KpiSkeleton />
      {Array.from({ length: 4 }, (_, index) => (
        <div key={index} className="flex gap-3 rounded-xl border border-border bg-surface p-3">
          <div className="h-8 w-8 shrink-0 animate-pulse rounded-full bg-surface-hover" />
          <div className="min-w-0 flex-1 animate-pulse space-y-2">
            <div className="h-3 w-2/5 rounded bg-surface-hover" />
            <div className="h-3 w-4/5 rounded bg-surface-hover" />
          </div>
        </div>
      ))}
    </div>
  );
}
