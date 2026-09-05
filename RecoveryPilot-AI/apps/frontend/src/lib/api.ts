import type { ApiEnvelope, PaginatedEnvelope } from "@/types/dashboard";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export class DashboardApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "DashboardApiError";
    this.status = status;
    this.code = code;
  }
}

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

/** GET JSON from the FastAPI envelope. Uses the Vite `/api` proxy by default. */
export async function getJson<T>(path: string, timeoutMs = 4_000): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new DashboardApiError("Dashboard API timed out", 408);
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
  const body = await parseBody(response);
  if (!response.ok) {
    const envelope = body as ApiEnvelope<unknown> | null;
    throw new DashboardApiError(
      envelope?.message ?? envelope?.error ?? `Request failed (${response.status})`,
      response.status,
      envelope?.code,
    );
  }
  return body as T;
}

export async function getData<T>(path: string, timeoutMs = 4_000): Promise<T> {
  const envelope = await getJson<ApiEnvelope<T>>(path, timeoutMs);
  if (!envelope.success || envelope.data == null) {
    throw new DashboardApiError(envelope.message || "Empty response", 502, envelope.code);
  }
  return envelope.data;
}

export async function getPage<T>(path: string, timeoutMs = 4_000): Promise<PaginatedEnvelope<T>> {
  return getJson<PaginatedEnvelope<T>>(path, timeoutMs);
}

/** POST JSON to the FastAPI envelope. Uses the Vite `/api` proxy by default. */
export async function postJson<T>(path: string, timeoutMs = 8_000): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      signal: controller.signal,
      body: "{}",
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new DashboardApiError("Dashboard API timed out", 408);
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
  const body = await parseBody(response);
  if (!response.ok) {
    const envelope = body as ApiEnvelope<unknown> | null;
    throw new DashboardApiError(
      envelope?.message ?? envelope?.error ?? `Request failed (${response.status})`,
      response.status,
      envelope?.code,
    );
  }
  return body as T;
}

/** POST and unwrap the FastAPI `data` field. */
export async function postData<T>(path: string, timeoutMs = 8_000): Promise<T> {
  const envelope = await postJson<ApiEnvelope<T>>(path, timeoutMs);
  if (!envelope.success || envelope.data == null) {
    throw new DashboardApiError(envelope.message || "Empty response", 502, envelope.code);
  }
  return envelope.data;
}
