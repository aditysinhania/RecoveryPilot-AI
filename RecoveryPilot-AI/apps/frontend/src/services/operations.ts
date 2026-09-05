import { getData } from "@/lib/api";
import type { OpsStatus } from "@/types/operations";

const FRONTEND_VERSION = import.meta.env.VITE_APP_VERSION ?? "0.1.0";
const FRONTEND_SHA = import.meta.env.VITE_BUILD_SHA ?? "dev";

/** Live operations snapshot from GET /ops/status. */
export async function fetchOpsStatus(): Promise<OpsStatus> {
  const data = await getData<OpsStatus>("/ops/status", 10_000);
  return {
    ...data,
    version: data.version || FRONTEND_VERSION,
    build_sha: data.build_sha || FRONTEND_SHA,
  };
}

export { FRONTEND_SHA, FRONTEND_VERSION };
