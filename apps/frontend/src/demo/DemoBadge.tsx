interface DemoBadgeProps {
  compact?: boolean;
}

/** Purple DEMO chip used across the public FitLife workspace. */
export function DemoBadge({ compact = false }: DemoBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full bg-ai-muted font-semibold uppercase tracking-wide text-ai ${
        compact ? "px-1.5 py-0.5 text-[9px]" : "px-2 py-0.5 text-[10px]"
      }`}
    >
      Demo
    </span>
  );
}
