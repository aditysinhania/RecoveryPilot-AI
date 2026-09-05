import { DashboardApiError } from "@/lib/api";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const BLOCKED_RETURN = new Set(["/login", "/signup"]);

/** Required work email with a simple format check. */
export function validateEmail(email: string): string | null {
  const trimmed = email.trim();
  if (!trimmed) {
    return "Email is required";
  }
  if (!EMAIL_RE.test(trimmed)) {
    return "Enter a valid email address";
  }
  return null;
}

/** Required password, default minimum 8 characters. */
export function validatePassword(password: string, minLength = 8): string | null {
  if (!password) {
    return "Password is required";
  }
  if (password.length < minLength) {
    return `Password must be at least ${minLength} characters`;
  }
  return null;
}

/** Non-empty trimmed text for name and similar fields. */
export function validateRequired(value: string, label: string): string | null {
  if (!value.trim()) {
    return `${label} is required`;
  }
  return null;
}

/**
 * Same-origin relative path only. Rejects protocol-relative URLs and auth routes
 * so `?next=` cannot bounce operators off-site or into a login loop.
 */
export function safeReturnPath(raw: string | null | undefined): string | null {
  if (!raw) {
    return null;
  }
  let value = raw.trim();
  try {
    value = decodeURIComponent(value);
  } catch {
    return null;
  }
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("://")) {
    return null;
  }
  if (value.includes("\\")) {
    return null;
  }
  const pathOnly = value.split("?")[0]?.split("#")[0] ?? "";
  if (!pathOnly || BLOCKED_RETURN.has(pathOnly)) {
    return null;
  }
  return value;
}

/** Append a safe `next` query param when present. */
export function withNextQuery(path: string, next: string | null | undefined): string {
  const safe = safeReturnPath(next);
  if (!safe) {
    return path;
  }
  return `${path}?next=${encodeURIComponent(safe)}`;
}

/** Signup/login destination: onboarding first, then dashboard or `?next=`. */
export function postAuthPath(
  user: { onboarding_completed: boolean },
  next: string | null | undefined,
): string {
  const safe = safeReturnPath(next);
  if (user.onboarding_completed) {
    return safe ?? "/dashboard";
  }
  return withNextQuery("/onboarding", safe);
}

/** Map API error codes to copy operators can act on. */
export function authErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof DashboardApiError) {
    switch (error.code) {
      case "database_unavailable":
        return (
          error.message ||
          "Can't reach PostgreSQL. Start it with docker compose up postgres, then try again."
        );
      case "auth_schema_missing":
        return (
          error.message ||
          "Auth tables are missing. Start PostgreSQL and restart the API, then try again."
        );
      case "email_taken":
        return "An account with this email already exists.";
      case "invalid_credentials":
        return "Invalid email or password";
      default:
        return error.message || fallback;
    }
  }
  return fallback;
}
