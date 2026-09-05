import { getData } from "@/lib/api";
import { runScenario, scenarioLabel } from "@/lib/simulatorLab";
import type { SavedScenario, ScenarioControls, ScenarioResult } from "@/types/simulatorLab";

const STORAGE_KEY = "rp.simulator-lab.v1";

interface SimulatorStatus {
  available: boolean;
  default_seed: number;
}

/** GET /simulator/status. Lab still runs from the snapshot if this fails. */
export async function fetchSimulatorStatus(): Promise<SimulatorStatus> {
  try {
    const data = await getData<SimulatorStatus>("/simulator/status", 3_000);
    return {
      available: Boolean(data.available),
      default_seed: data.default_seed ?? 42,
    };
  } catch {
    return { available: true, default_seed: 42 };
  }
}

function readStore(): SavedScenario[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((row) => row && typeof row === "object" && "id" in row && "controls" in row) as SavedScenario[];
  } catch {
    return [];
  }
}

function writeStore(rows: SavedScenario[]): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(rows));
}

/** Load saved playground scenarios from localStorage. */
export function listSavedScenarios(): SavedScenario[] {
  return readStore().sort((a, b) => b.saved_at.localeCompare(a.saved_at));
}

/** Persist the current run. Frontend state only. */
export function saveScenario(result: ScenarioResult, name?: string): SavedScenario {
  const row: SavedScenario = {
    id: typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `scn-${Date.now()}`,
    name: name?.trim() || scenarioLabel(result.controls),
    saved_at: new Date().toISOString(),
    controls: { ...result.controls },
    result: { ...result, controls: { ...result.controls } },
  };
  writeStore([row, ...readStore()].slice(0, 24));
  return row;
}

/** Remove one saved scenario. */
export function deleteSavedScenario(id: string): SavedScenario[] {
  const next = readStore().filter((row) => row.id !== id);
  writeStore(next);
  return next.sort((a, b) => b.saved_at.localeCompare(a.saved_at));
}

/** Re-run a saved control set through the same display map. */
export function replaySavedScenario(controls: ScenarioControls): ScenarioResult {
  return runScenario(controls);
}
