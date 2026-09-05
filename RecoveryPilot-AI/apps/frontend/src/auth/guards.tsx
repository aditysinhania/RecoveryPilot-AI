import { Navigate, Outlet, useLocation, useSearchParams } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { postAuthPath, safeReturnPath, withNextQuery } from "@/lib/authForm";

function Restoring() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas text-sm text-muted">
      Restoring session…
    </div>
  );
}

/** Block dashboard routes until a valid session exists. */
export function RequireAuth() {
  const { user, ready } = useAuth();
  const location = useLocation();

  if (!ready) {
    return <Restoring />;
  }
  if (!user) {
    const next = `${location.pathname}${location.search}`;
    return <Navigate to={withNextQuery("/login", next)} replace />;
  }
  return <Outlet />;
}

/** Send authenticated users who finished onboarding away from login/signup. */
export function GuestOnly() {
  const { user, ready } = useAuth();
  const [params] = useSearchParams();
  const next = safeReturnPath(params.get("next"));

  if (!ready) {
    return <Restoring />;
  }
  if (user) {
    return <Navigate to={postAuthPath(user, next)} replace />;
  }
  return <Outlet />;
}

/** Onboarding must finish before merchant ops chrome. */
export function RequireOnboarding() {
  const { user, ready } = useAuth();
  const location = useLocation();

  if (!ready) {
    return <Restoring />;
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  if (!user.onboarding_completed) {
    const next = `${location.pathname}${location.search}`;
    return <Navigate to={withNextQuery("/onboarding", next)} replace />;
  }
  return <Outlet />;
}

/** Authenticated users who already onboarded skip the wizard. */
export function OnboardingGate() {
  const { user, ready } = useAuth();
  const [params] = useSearchParams();

  if (!ready || !user) {
    return <Outlet />;
  }
  if (user.onboarding_completed) {
    return <Navigate to={safeReturnPath(params.get("next")) ?? "/dashboard"} replace />;
  }
  return <Outlet />;
}
