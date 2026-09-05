import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { AuthSubmitButton } from "@/components/auth/AuthSubmitButton";
import { PasswordField } from "@/components/auth/PasswordField";
import {
  authErrorMessage,
  postAuthPath,
  safeReturnPath,
  validateEmail,
  validatePassword,
  withNextQuery,
} from "@/lib/authForm";

/** Email/password sign-in. */
export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeReturnPath(params.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const nextEmailError = validateEmail(email);
    const nextPasswordError = validatePassword(password);
    setEmailError(nextEmailError);
    setPasswordError(nextPasswordError);
    setError(null);
    if (nextEmailError || nextPasswordError) {
      return;
    }
    setPending(true);
    try {
      const user = await login(email.trim(), password);
      navigate(postAuthPath(user, next), { replace: true });
    } catch (err) {
      setError(authErrorMessage(err, "Sign in failed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthLayout
      title="Sign in"
      subtitle="Merchant operators only. Use the email you registered with."
      footer={
        <>
          New to RecoveryPilot?{" "}
          <Link to={withNextQuery("/signup", next)} className="text-info hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form className="space-y-3" onSubmit={(event) => void onSubmit(event)}>
        <label className="block text-sm">
          <span className="text-muted">Email</span>
          <input
            type="text"
            inputMode="email"
            autoComplete="email"
            value={email}
            disabled={pending}
            onChange={(event) => {
              setEmail(event.target.value);
              if (emailError) {
                setEmailError(null);
              }
            }}
            className={`mt-1 w-full rounded-lg border bg-canvas px-3 py-2 text-sm outline-none focus:border-ai ${
              emailError ? "border-blocked" : "border-border"
            }`}
          />
          {emailError ? <p className="mt-1 text-xs text-blocked">{emailError}</p> : null}
        </label>
        <PasswordField
          label="Password"
          value={password}
          autoComplete="current-password"
          error={passwordError}
          disabled={pending}
          onChange={(value) => {
            setPassword(value);
            if (passwordError) {
              setPasswordError(null);
            }
          }}
        />
        {error ? <p className="text-sm text-blocked">{error}</p> : null}
        <AuthSubmitButton pending={pending} idleLabel="Sign in" pendingLabel="Signing in…" />
      </form>
    </AuthLayout>
  );
}
