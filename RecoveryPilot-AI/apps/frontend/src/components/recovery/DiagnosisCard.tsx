import { formatPercent, titleCase } from "@/lib/format";
import type { CaseDrawerModel } from "@/types/recovery";

interface DiagnosisCardProps {
  diagnosis: CaseDrawerModel["diagnosis"];
}

function confidenceTone(score: number): { label: string; bar: string; badge: string } {
  if (score >= 0.75) {
    return { label: "High", bar: "bg-recovered", badge: "bg-recovered-muted text-recovered" };
  }
  if (score >= 0.5) {
    return { label: "Medium", bar: "bg-waiting", badge: "bg-waiting-muted text-waiting" };
  }
  return { label: "Low", bar: "bg-blocked", badge: "bg-blocked-muted text-blocked" };
}

/** Primary diagnosis, confidence bar, evidence weights, rules, and model badge. */
export function DiagnosisCard({ diagnosis }: DiagnosisCardProps) {
  const pct = Math.round(diagnosis.confidence * 100);
  const tone = confidenceTone(diagnosis.confidence);
  return (
    <section className="rounded-xl border border-border bg-surface-raised p-4" aria-labelledby="diagnosis-heading">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 id="diagnosis-heading" className="text-[11px] font-semibold uppercase tracking-wide text-muted">
            Diagnosis
          </h3>
          <p className="mt-1 text-sm font-medium text-foreground">{titleCase(diagnosis.primary)}</p>
        </div>
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${tone.badge}`}>
          {tone.label} · {formatPercent(diagnosis.confidence, 0)}
        </span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-zinc-800" aria-hidden>
        <div className={`h-full rounded-full ${tone.bar}`} style={{ width: `${pct}%` }} />
      </div>
      <ul className="mt-3 space-y-2.5">
        {diagnosis.evidence.map((item) => (
          <li key={item.label}>
            <div className="flex justify-between gap-2 text-xs text-foreground">
              <span>{item.label}</span>
              <span className="tabular-nums text-muted">{formatPercent(item.weight, 0)}</span>
            </div>
            <div className="mt-1 h-1 overflow-hidden rounded-full bg-zinc-800" aria-hidden>
              <div className="h-full rounded-full bg-ai" style={{ width: `${Math.round(item.weight * 100)}%` }} />
            </div>
            <p className="mt-1 text-[11px] text-muted">{item.message}</p>
          </li>
        ))}
      </ul>
      {diagnosis.triggered_rules.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1">
          {diagnosis.triggered_rules.map((rule) => (
            <span key={rule} className="rounded-full bg-zinc-800 px-2 py-0.5 font-mono text-[10px] text-zinc-400">
              {rule}
            </span>
          ))}
        </div>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-1.5">
        <span className="rounded-full bg-ai-muted px-2 py-0.5 text-[10px] font-medium text-ai">{diagnosis.model}</span>
        <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-muted">v{diagnosis.version}</span>
      </div>
    </section>
  );
}
