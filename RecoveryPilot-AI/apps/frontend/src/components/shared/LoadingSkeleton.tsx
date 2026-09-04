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
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {Array.from({ length: 6 }, (_, index) => (
          <LoadingSkeleton key={index} lines={2} />
        ))}
      </div>
      <LoadingSkeleton lines={3} className="h-28" />
      <div className="grid gap-4 lg:grid-cols-2">
        <LoadingSkeleton lines={6} className="h-48" />
        <LoadingSkeleton lines={6} className="h-48" />
      </div>
    </div>
  );
}
