import { conditionChips, MERCHANT_PROFILES } from "@/lib/simulatorLab";
import type { ScenarioResult } from "@/types/simulatorLab";

interface ScenarioSummaryCardProps {
  result: ScenarioResult;
}

/** Active merchant profile and condition chips for the last run. */
export function ScenarioSummaryCard({ result }: ScenarioSummaryCardProps) {
  const profile = MERCHANT_PROFILES[result.controls.merchant];
  const chips = conditionChips(result.controls);
  return (
    <section className="rounded-xl border border-border bg-surface p-3 shadow-[var(--shadow-card)]">
      <p className="text-[10px] font-medium uppercase tracking-wide text-muted">Scenario summary</p>
      <h2 className="mt-1 text-sm font-semibold text-foreground">{profile.merchant_name}</h2>
      <p className="mt-0.5 text-[11px] text-muted">{profile.notes}</p>
      <p className="mt-1 text-[11px] text-muted">
        {result.customers.toLocaleString("en-IN")} customers · {result.cases.toLocaleString("en-IN")} failed invoices
        {result.source === "snapshot" ? " · exact seed-42 snapshot" : " · scaled from seed 42"}
      </p>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {chips.map((chip) => (
          <li
            key={chip.label}
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
              chip.active ? "bg-ai-muted text-ai" : "bg-zinc-800 text-zinc-500 line-through"
            }`}
          >
            {chip.label}
          </li>
        ))}
      </ul>
    </section>
  );
}
