import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { AuthSubmitButton } from "@/components/auth/AuthSubmitButton";
import { PasswordField } from "@/components/auth/PasswordField";
import {
  authErrorMessage,
  safeReturnPath,
  validateEmail,
  validatePassword,
  validateRequired,
  withNextQuery,
} from "@/lib/authForm";

/** Create a merchant operator account. */
export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = safeReturnPath(params.get("next"));
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const nextNameError = validateRequired(fullName, "Full name");
    const nextEmailError = validateEmail(email);
    const nextPasswordError = validatePassword(password);
    setNameError(nextNameError);
    setEmailError(nextEmailError);
    setPasswordError(nextPasswordError);
    setError(null);
    if (nextNameError || nextEmailError || nextPasswordError) {
      return;
    }
    setPending(true);
    try {
      await signup({ email: email.trim(), password, full_name: fullName.trim() });
      navigate(withNextQuery("/onboarding", next), { replace: true });
    } catch (err) {
      setError(authErrorMessage(err, "Sign up failed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <AuthLayout
      title="Create your workspace"
      subtitle="Takes a minute. Razorpay Sandbox keys come in onboarding."
      footer={
        <>
          Already have an account?{" "}
          <Link to={withNextQuery("/login", next)} className="text-info hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form className="space-y-3" onSubmit={(event) => void onSubmit(event)}>
        <label className="block text-sm">
          <span className="text-muted">Full name</span>
          <input
            autoComplete="name"
            value={fullName}
            disabled={pending}
            onChange={(event) => {
              setFullName(event.target.value);
              if (nameError) {
                setNameError(null);
              }
            }}
            className={`mt-1 w-full rounded-lg border bg-canvas px-3 py-2 text-sm outline-none focus:border-ai ${
              nameError ? "border-blocked" : "border-border"
            }`}
          />
          {nameError ? <p className="mt-1 text-xs text-blocked">{nameError}</p> : null}
        </label>
        <label className="block text-sm">
          <span className="text-muted">Work email</span>
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
          label="Password (8+ characters)"
          value={password}
          autoComplete="new-password"
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
        <AuthSubmitButton pending={pending} idleLabel="Create account" pendingLabel="Creating account…" />
      </form>
    </AuthLayout>
  );
}
