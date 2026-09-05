import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { DashboardApiError } from "@/lib/api";
import { clearTokens, getAccessToken } from "@/lib/tokens";
import { fetchMe, login as loginRequest, logout as logoutRequest, signup as signupRequest } from "@/services/auth";
import type { AuthUser } from "@/types/auth";

interface AuthContextValue {
  user: AuthUser | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<AuthUser>;
  signup: (input: { email: string; password: string; full_name: string }) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<AuthUser | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Session bootstrap from stored JWTs plus login/signup/logout. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [ready, setReady] = useState(false);

  const refreshUser = useCallback(async (): Promise<AuthUser | null> => {
    if (!getAccessToken()) {
      setUser(null);
      return null;
    }
    try {
      const me = await fetchMe();
      setUser(me);
      return me;
    } catch (error) {
      if (error instanceof DashboardApiError && error.status === 401) {
        clearTokens();
        setUser(null);
        return null;
      }
      throw error;
    }
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        await refreshUser();
      } catch {
        setUser(null);
      } finally {
        setReady(true);
      }
    })();
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string) => {
    const payload = await loginRequest({ email, password });
    setUser(payload.user);
    return payload.user;
  }, []);

  const signup = useCallback(async (input: { email: string; password: string; full_name: string }) => {
    const payload = await signupRequest(input);
    setUser(payload.user);
    return payload.user;
  }, []);

  const logout = useCallback(async () => {
    await logoutRequest();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, ready, login, signup, logout, refreshUser }),
    [user, ready, login, signup, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Access the auth session. Must be used under AuthProvider. */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
