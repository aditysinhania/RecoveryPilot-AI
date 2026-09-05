import { DashboardApiError, getData, postBody } from "@/lib/api";
import { clearTokens, setTokens } from "@/lib/tokens";
import type { AuthUser, TokenPayload } from "@/types/auth";

function persist(payload: TokenPayload): TokenPayload {
  setTokens(payload.access_token, payload.refresh_token);
  return payload;
}

/** Register a merchant operator and store JWTs. */
export async function signup(input: {
  email: string;
  password: string;
  full_name: string;
}): Promise<TokenPayload> {
  return persist(await postBody<TokenPayload>("/auth/signup", input, 12_000));
}

/** Email/password login. */
export async function login(input: { email: string; password: string }): Promise<TokenPayload> {
  return persist(await postBody<TokenPayload>("/auth/login", input, 12_000));
}

/** Load the current operator. Throws DashboardApiError 401 when signed out. */
export async function fetchMe(): Promise<AuthUser> {
  return getData<AuthUser>("/auth/me", 8_000);
}

/** Revoke the refresh session and drop local JWTs. */
export async function logout(): Promise<void> {
  const refresh = window.localStorage.getItem("rp_refresh_token");
  try {
    if (refresh) {
      await postBody("/auth/logout", { refresh_token: refresh }, 6_000);
    }
  } catch (error) {
    if (!(error instanceof DashboardApiError)) {
      throw error;
    }
  } finally {
    clearTokens();
  }
}
