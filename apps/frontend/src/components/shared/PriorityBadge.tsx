interface PriorityBadgeProps {
  score: number;
}

function labelFor(score: number): { text: string; cls: string } {
  if (score >= 0.8) {
    return { text: "High", cls: "bg-blocked-muted text-blocked" };
  }
  if (score >= 0.6) {
    return { text: "Medium", cls: "bg-waiting-muted text-waiting" };
  }
  return { text: "Low", cls: "bg-zinc-800 text-muted" };
}

/** Priority from the engine score (HIGH ≥ 0.8, MEDIUM 0.6–0.8, LOW < 0.6). */
export function PriorityBadge({ score }: PriorityBadgeProps) {
  const { text, cls } = labelFor(score);
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium ${cls}`}>
      {text}
    </span>
  );
}
