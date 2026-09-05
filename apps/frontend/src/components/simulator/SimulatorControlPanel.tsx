import type { ChangeEvent, ReactNode } from "react";
import { FlaskConical, RotateCcw, Save, Play } from "lucide-react";
import { BASELINE_STRATEGIES, MERCHANT_KEYS, SIMULATOR_SEEDS } from "@/types/simulatorLab";
import { baselineLabel, MERCHANT_PROFILES } from "@/lib/simulatorLab";
import type { MerchantKey, ScenarioControls } from "@/types/simulatorLab";

interface SimulatorControlPanelProps {
  draft: ScenarioControls;
  dirty: boolean;
  computing: boolean;
  onPatch: (partial: Partial<ScenarioControls>) => void;
  onRun: () => void;
  onReset: () => void;
  onSave: () => void;
}

const CONTROL =
  "h-8 w-full rounded-md border border-border bg-canvas px-2.5 text-xs text-foreground";

function Field({
  id,
  label,
  children,
}: {
  id: string;
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block" htmlFor={id}>
      <span className="mb-0.5 block text-[10px] font-medium uppercase tracking-wide text-muted">{label}</span>
      {children}
    </label>
  );
}

/** Sticky playground knobs. Run applies the draft; engines are never invoked. */
export function SimulatorControlPanel({
  draft,
  dirty,
  computing,
  onPatch,
  onRun,
  onReset,
  onSave,
}: SimulatorControlPanelProps) {
  const onMerchant = (event: ChangeEvent<HTMLSelectElement>): void => {
    const merchant = event.target.value as MerchantKey;
    onPatch({
      merchant,
      festivalCalendar: MERCHANT_PROFILES[merchant].festival_default,
    });
  };

  return (
    <section
      className="lg:sticky lg:top-3 space-y-3 rounded-xl border border-border bg-surface/95 p-3 shadow-[var(--shadow-card)] backdrop-blur"
      aria-label="Simulation controls"
    >
      <div className="flex items-center gap-2">
        <FlaskConical size={14} className="text-ai" aria-hidden />
        <h2 className="text-sm font-semibold">Simulation controls</h2>
        {dirty ? (
          <span className="rounded-full bg-waiting-muted px-2 py-0.5 text-[10px] font-medium text-waiting">
            Unapplied
          </span>
        ) : null}
      </div>

      <Field id="sim-merchant" label="Merchant type">
        <select id="sim-merchant" className={CONTROL} value={draft.merchant} onChange={onMerchant}>
          {MERCHANT_KEYS.map((key) => (
            <option key={key} value={key}>
              {MERCHANT_PROFILES[key].label}
            </option>
          ))}
        </select>
      </Field>

      <Field id="sim-customers" label={`Customer count · ${draft.customerCount.toLocaleString("en-IN")}`}>
        <input
          id="sim-customers"
          type="range"
          min={100}
          max={5000}
          step={50}
          value={draft.customerCount}
          onChange={(event) => onPatch({ customerCount: Number(event.target.value) })}
          className="w-full accent-sky-400"
        />
      </Field>

      <Field id="sim-fail" label={`Failure rate · ${(draft.failureRate * 100).toFixed(0)}%`}>
        <input
          id="sim-fail"
          type="range"
          min={5}
          max={40}
          step={1}
          value={Math.round(draft.failureRate * 100)}
          onChange={(event) => onPatch({ failureRate: Number(event.target.value) / 100 })}
          className="w-full accent-sky-400"
        />
      </Field>

      <fieldset className="space-y-1.5">
        <legend className="text-[10px] font-medium uppercase tracking-wide text-muted">Conditions</legend>
        {(
          [
            ["salaryCycle", "Salary cycle"],
            ["festivalCalendar", "Festival calendar"],
            ["bankDowntime", "NPCI / bank downtime"],
            ["promiseToPay", "Promise-to-pay enabled"],
          ] as const
        ).map(([key, label]) => (
          <label key={key} className="flex items-center justify-between gap-2 text-xs text-foreground">
            <span>{label}</span>
            <input
              type="checkbox"
              checked={draft[key]}
              onChange={(event) => onPatch({ [key]: event.target.checked })}
              className="h-4 w-4 accent-violet-400"
            />
          </label>
        ))}
      </fieldset>

      <Field id="sim-baseline" label="Baseline retry strategy">
        <select
          id="sim-baseline"
          className={CONTROL}
          value={draft.baselineStrategy}
          onChange={(event) => onPatch({ baselineStrategy: event.target.value as ScenarioControls["baselineStrategy"] })}
        >
          {BASELINE_STRATEGIES.map((value) => (
            <option key={value} value={value}>
              {baselineLabel(value)}
            </option>
          ))}
        </select>
      </Field>

      <Field id="sim-seed" label="Random seed">
        <select
          id="sim-seed"
          className={CONTROL}
          value={draft.seed}
          onChange={(event) => onPatch({ seed: Number(event.target.value) })}
        >
          {SIMULATOR_SEEDS.map((value) => (
            <option key={value} value={value}>
              {value === 42 ? "42 (default FitLife)" : String(value)}
            </option>
          ))}
        </select>
      </Field>

      <div className="grid grid-cols-1 gap-1.5">
        <button
          type="button"
          onClick={onRun}
          disabled={computing}
          className="inline-flex h-8 items-center justify-center gap-1.5 rounded-md bg-info-muted px-2.5 text-xs font-medium text-info hover:bg-info/20 disabled:opacity-40"
        >
          <Play size={13} aria-hidden />
          Run simulation
        </button>
        <div className="grid grid-cols-2 gap-1.5">
          <button
            type="button"
            onClick={onReset}
            disabled={computing}
            className="inline-flex h-8 items-center justify-center gap-1 rounded-md border border-border px-2 text-xs text-foreground hover:bg-surface-hover disabled:opacity-40"
          >
            <RotateCcw size={13} aria-hidden />
            Seed 42
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={computing}
            className="inline-flex h-8 items-center justify-center gap-1 rounded-md border border-border px-2 text-xs text-foreground hover:bg-surface-hover disabled:opacity-40"
          >
            <Save size={13} aria-hidden />
            Save
          </button>
        </div>
      </div>
    </section>
  );
}
