const ACCESS_KEY = "rp_access_token";
const REFRESH_KEY = "rp_refresh_token";

/** Read the short-lived access JWT from localStorage. */
export function getAccessToken(): string | null {
  return window.localStorage.getItem(ACCESS_KEY);
}

/** Read the refresh JWT from localStorage. */
export function getRefreshToken(): string | null {
  return window.localStorage.getItem(REFRESH_KEY);
}

/** Persist both JWTs after signup, login, or refresh. */
export function setTokens(accessToken: string, refreshToken: string): void {
  window.localStorage.setItem(ACCESS_KEY, accessToken);
  window.localStorage.setItem(REFRESH_KEY, refreshToken);
}

/** Clear JWTs on logout or revoked refresh. */
export function clearTokens(): void {
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}
