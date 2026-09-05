import { clearTokens, getAccessToken, getRefreshToken, setTokens } from "@/lib/tokens";
import type { ApiEnvelope, PaginatedEnvelope } from "@/types/dashboard";

function resolveApiBase(): string {
  if (import.meta.env.DEV) {
    return "/api/v1";
  }
  const raw = String(import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");
  if (raw.endsWith("/api/v1")) {
    return raw;
  }
  if (raw.endsWith("/api")) {
    return `${raw}/v1`;
  }
  if (/^https?:\/\//.test(raw)) {
    return `${raw}/api/v1`;
  }
  return raw || "/api/v1";
}

const API_BASE = resolveApiBase();
const AUTH_PATHS = ["/auth/login", "/auth/signup", "/auth/refresh", "/auth/logout"];

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

function headersFor(path: string, hasBody: boolean): HeadersInit {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (hasBody) {
    headers["Content-Type"] = "application/json";
  }
  const token = getAccessToken();
  if (token && !AUTH_PATHS.includes(path)) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

let refreshInFlight: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (refreshInFlight) {
    return refreshInFlight;
  }
  refreshInFlight = (async () => {
    const refresh = getRefreshToken();
    if (!refresh) {
      return false;
    }
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      const body = (await parseBody(response)) as ApiEnvelope<{
        access_token: string;
        refresh_token: string;
      }> | null;
      if (!response.ok || !body?.data?.access_token) {
        clearTokens();
        return false;
      }
      setTokens(body.data.access_token, body.data.refresh_token);
      return true;
    } catch {
      clearTokens();
      return false;
    }
  })();
  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  timeoutMs?: number;
  retryOnUnauthorized?: boolean;
}

/** Fetch JSON from the FastAPI envelope. Attaches the access JWT when present. */
export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const timeoutMs = options.timeoutMs ?? 8_000;
  const hasBody = options.body !== undefined;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: headersFor(path, hasBody),
      signal: controller.signal,
      body: hasBody ? JSON.stringify(options.body) : undefined,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new DashboardApiError("Dashboard API timed out", 408);
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
  if (
    response.status === 401 &&
    options.retryOnUnauthorized !== false &&
    !AUTH_PATHS.includes(path)
  ) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      return requestJson<T>(path, { ...options, retryOnUnauthorized: false });
    }
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

/** GET JSON from the FastAPI envelope. Uses the Vite `/api` proxy by default. */
export async function getJson<T>(path: string, timeoutMs = 4_000): Promise<T> {
  return requestJson<T>(path, { method: "GET", timeoutMs });
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
  return requestJson<T>(path, { method: "POST", body: {}, timeoutMs });
}

/** POST and unwrap the FastAPI `data` field. */
export async function postData<T>(path: string, timeoutMs = 8_000): Promise<T> {
  const envelope = await postJson<ApiEnvelope<T>>(path, timeoutMs);
  if (!envelope.success || envelope.data == null) {
    throw new DashboardApiError(envelope.message || "Empty response", 502, envelope.code);
  }
  return envelope.data;
}

/** POST a JSON body and unwrap `data`. */
export async function postBody<T>(path: string, body: unknown, timeoutMs = 8_000): Promise<T> {
  const envelope = await requestJson<ApiEnvelope<T>>(path, { method: "POST", body, timeoutMs });
  if (!envelope.success || envelope.data == null) {
    throw new DashboardApiError(envelope.message || "Empty response", 502, envelope.code);
  }
  return envelope.data;
}

/** PATCH a JSON body and unwrap `data`. */
export async function patchBody<T>(path: string, body: unknown, timeoutMs = 8_000): Promise<T> {
  const envelope = await requestJson<ApiEnvelope<T>>(path, { method: "PATCH", body, timeoutMs });
  if (!envelope.success || envelope.data == null) {
    throw new DashboardApiError(envelope.message || "Empty response", 502, envelope.code);
  }
  return envelope.data;
}
