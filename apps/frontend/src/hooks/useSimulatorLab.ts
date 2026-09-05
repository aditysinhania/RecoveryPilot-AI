import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { controlsEqual, DEFAULT_CONTROLS, runScenario, SEED_42_RESULT } from "@/lib/simulatorLab";
import {
  deleteSavedScenario,
  fetchSimulatorStatus,
  listSavedScenarios,
  saveScenario,
} from "@/services/simulatorLab";
import type { SavedScenario, ScenarioControls, ScenarioResult } from "@/types/simulatorLab";

const COMPUTE_MS = 280;

/** Playground state: draft knobs, last run, saved list. Snapshot-only recompute. */
export function useSimulatorLab() {
  const [draft, setDraft] = useState<ScenarioControls>({ ...DEFAULT_CONTROLS });
  const [result, setResult] = useState<ScenarioResult>(SEED_42_RESULT);
  const [computing, setComputing] = useState(false);
  const [saved, setSaved] = useState<SavedScenario[]>(() =>
    typeof window === "undefined" ? [] : listSavedScenarios(),
  );
  const [drawerOpen, setDrawerOpen] = useState(false);

  const statusQuery = useQuery({
    queryKey: ["simulator-status"],
    queryFn: fetchSimulatorStatus,
    staleTime: 60_000,
    retry: 0,
  });

  useEffect(() => {
    setSaved(listSavedScenarios());
  }, []);

  const patchDraft = useCallback((partial: Partial<ScenarioControls>): void => {
    setDraft((current) => ({ ...current, ...partial }));
  }, []);

  const run = useCallback((controls: ScenarioControls = draft): void => {
    setComputing(true);
    window.setTimeout(() => {
      setResult(runScenario(controls));
      setDraft(controls);
      setComputing(false);
    }, COMPUTE_MS);
  }, [draft]);

  const resetSeed42 = useCallback((): void => {
    run({ ...DEFAULT_CONTROLS });
  }, [run]);

  const persist = useCallback((): SavedScenario | null => {
    if (computing) {
      return null;
    }
    const row = saveScenario(result);
    setSaved(listSavedScenarios());
    return row;
  }, [computing, result]);

  const reloadSaved = useCallback(
    (row: SavedScenario): void => {
      run(row.controls);
    },
    [run],
  );

  const removeSaved = useCallback((id: string): void => {
    setSaved(deleteSavedScenario(id));
  }, []);

  const dirty = useMemo(() => !controlsEqual(draft, result.controls), [draft, result.controls]);

  return {
    draft,
    patchDraft,
    result,
    seed42: SEED_42_RESULT,
    computing,
    dirty,
    saved,
    drawerOpen,
    setDrawerOpen,
    run: (): void => run(draft),
    resetSeed42,
    persist,
    reloadSaved,
    removeSaved,
    status: statusQuery.data ?? { available: true, default_seed: 42 },
    statusSource: statusQuery.isError ? "snapshot" : "live",
  };
}
