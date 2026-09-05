import { RotateCcw, Trash2 } from "lucide-react";
import { conditionChips } from "@/lib/simulatorLab";
import { formatDateTime } from "@/lib/format";
import type { SavedScenario } from "@/types/simulatorLab";

interface SavedScenarioCardProps {
  row: SavedScenario;
  onReload: (row: SavedScenario) => void;
  onDelete: (id: string) => void;
}

/** One localStorage scenario with reload and delete. */
export function SavedScenarioCard({ row, onReload, onDelete }: SavedScenarioCardProps) {
  const chips = conditionChips(row.controls).filter((chip) => chip.active).slice(0, 5);
  return (
    <article className="rounded-xl border border-border bg-surface p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-sm font-semibold text-foreground">{row.name}</h3>
          <p className="mt-0.5 text-[11px] text-muted">{formatDateTime(row.saved_at)}</p>
        </div>
        <div className="flex shrink-0 gap-1">
          <button
            type="button"
            className="inline-flex h-7 items-center gap-1 rounded-md border border-border px-2 text-[11px] hover:bg-surface-hover"
            onClick={() => onReload(row)}
          >
            <RotateCcw size={12} aria-hidden />
            Reload
          </button>
          <button
            type="button"
            className="inline-flex h-7 items-center gap-1 rounded-md border border-border px-2 text-[11px] text-blocked hover:bg-blocked-muted"
            onClick={() => onDelete(row.id)}
          >
            <Trash2 size={12} aria-hidden />
            Delete
          </button>
        </div>
      </div>
      <ul className="mt-2 flex flex-wrap gap-1">
        {chips.map((chip) => (
          <li key={chip.label} className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-muted">
            {chip.label}
          </li>
        ))}
      </ul>
    </article>
  );
}
