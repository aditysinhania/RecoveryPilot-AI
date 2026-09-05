import { getData, postData } from "@/lib/api";
import type { ActionDashboardSummary, ActionExecution, ActionStatus } from "@/types/actions";

const FETCH_MS = 4_000;

/** Live execution status for one recovery case. */
export async function fetchActionStatus(caseId: string): Promise<ActionStatus> {
  return getData<ActionStatus>(`/actions/${caseId}/status`, FETCH_MS);
}

/** Execute the current RecoveryPlan against Razorpay Sandbox. */
export async function executeAction(caseId: string): Promise<ActionExecution> {
  return postData<ActionExecution>(`/actions/${caseId}/execute`);
}

/** Schedule WAIT_FOR_PAYDAY / HONOUR_PROMISE_TO_PAY without executing now. */
export async function scheduleAction(caseId: string): Promise<ActionExecution> {
  return postData<ActionExecution>(`/actions/${caseId}/schedule`);
}

/** Idempotent replay of one execution. */
export async function replayAction(executionId: string): Promise<ActionExecution> {
  return postData<ActionExecution>(`/actions/replay/${executionId}`);
}

/** Merchant orchestrator KPIs and per-case action chips. */
export async function fetchActionSummary(merchantId?: string): Promise<ActionDashboardSummary> {
  const query = merchantId ? `?merchant_id=${encodeURIComponent(merchantId)}` : "";
  return getData<ActionDashboardSummary>(`/actions/summary${query}`, FETCH_MS);
}
