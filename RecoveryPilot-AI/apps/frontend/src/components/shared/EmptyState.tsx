interface EmptyStateProps {
  title: string;
  description: string;
  compact?: boolean;
}

/** Empty dataset placeholder. */
export function EmptyState({ title, description, compact = false }: EmptyStateProps) {
  return (
    <div
      className={`rounded-xl border border-dashed border-border text-center ${
        compact ? "px-3 py-4" : "px-6 py-10"
      }`}
    >
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="mt-1 text-xs text-muted">{description}</p>
    </div>
  );
}

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  compact?: boolean;
}

/** Recoverable fetch error. */
export function ErrorState({ message, onRetry, compact = false }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={`flex flex-wrap items-center justify-between gap-2 rounded-xl border border-blocked/40 bg-blocked-muted ${
        compact ? "px-3 py-1.5" : "px-4 py-3"
      }`}
    >
      <p className={compact ? "text-xs text-blocked" : "text-sm text-blocked"}>{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-lg bg-surface px-3 py-1.5 text-xs font-medium text-foreground"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
