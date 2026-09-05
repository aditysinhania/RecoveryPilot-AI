import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/auth/AuthProvider";
import { AuthSubmitButton } from "@/components/auth/AuthSubmitButton";
import { PasswordField } from "@/components/auth/PasswordField";
import { authErrorMessage, safeReturnPath } from "@/lib/authForm";
import { razorpayKeyIdError, razorpayKeysLookValid, razorpaySecretError } from "@/lib/razorpayKeys";
import {
  COMPANY_SIZES,
  loadAiStepDone,
  loadOnboardingExtras,
  MONTHLY_VOLUMES,
  saveAiStepDone,
  saveOnboardingExtras,
} from "@/lib/workspacePrefs";
import {
  completeWorkspace,
  fetchBusinessTypes,
  saveBusinessType,
  saveMerchantInfo,
  saveRazorpayKeys,
} from "@/services/onboarding";
import { updateGemini, updateNotifications } from "@/services/account";
import { useToast } from "@/toast/ToastProvider";

const STEPS = ["Merchant Profile", "Razorpay Sandbox", "AI Configuration", "Workspace"] as const;

function uiStep(backendStep: number, aiDone: boolean): number {
  if (backendStep <= 2) {
    return 1;
  }
  if (backendStep === 3) {
    return 2;
  }
  return aiDone ? 4 : 3;
}

/** Four-step merchant onboarding wizard. Extra fields stay in localStorage. */
export default function OnboardingPage() {
  const { user, refreshUser, logout } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const toast = useToast();
  const extras = loadOnboardingExtras();
  const [step, setStep] = useState(() => uiStep(user?.onboarding_step ?? 1, loadAiStepDone()));
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [testing, setTesting] = useState(false);
  const [types, setTypes] = useState<string[]>([]);
  const [merchantName, setMerchantName] = useState(user?.merchant_name ?? "");
  const [businessType, setBusinessType] = useState("Fitness & Wellness");
  const [companySize, setCompanySize] = useState(extras.company_size);
  const [monthlyVolume, setMonthlyVolume] = useState(extras.monthly_volume);
  const [keyId, setKeyId] = useState("");
  const [keySecret, setKeySecret] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [aiExplanations, setAiExplanations] = useState(extras.ai_explanations);
  const [notifyRecovery, setNotifyRecovery] = useState(true);
  const [notifyDigest, setNotifyDigest] = useState(true);
  const [notifyWebhook, setNotifyWebhook] = useState(true);
  const [workspaceKind, setWorkspaceKind] = useState<"demo" | "empty">("demo");

  useEffect(() => {
    void fetchBusinessTypes().then(setTypes);
  }, []);

  async function goDashboard() {
    const next = await refreshUser();
    if (next?.onboarding_completed) {
      toast.success("Workspace saved", "Your merchant workspace is ready.");
      navigate(safeReturnPath(params.get("next")) ?? "/dashboard", { replace: true });
    }
  }

  async function onStep1(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      saveOnboardingExtras({
        company_size: companySize,
        monthly_volume: monthlyVolume,
        ai_explanations: aiExplanations,
      });
      await saveMerchantInfo({ merchant_name: merchantName, phone: "", timezone: "Asia/Kolkata" });
      await saveBusinessType(businessType);
      setStep(2);
      await refreshUser();
    } catch (err) {
      setError(authErrorMessage(err, "Could not save merchant profile"));
    } finally {
      setPending(false);
    }
  }

  async function onStep2(event: FormEvent) {
    event.preventDefault();
    const keyErr = razorpayKeyIdError(keyId);
    const secretErr = razorpaySecretError(keySecret);
    if (keyErr || secretErr) {
      setError(keyErr ?? secretErr);
      toast.error("Invalid Razorpay keys", keyErr ?? secretErr ?? undefined);
      return;
    }
    setPending(true);
    setError(null);
    try {
      await saveRazorpayKeys({
        key_id: keyId,
        key_secret: keySecret,
        webhook_secret: webhookSecret,
      });
      setStep(3);
      await refreshUser();
    } catch (err) {
      setError(authErrorMessage(err, "Could not save Razorpay keys"));
      toast.error("Failed connection", "Razorpay Sandbox keys were not stored.");
    } finally {
      setPending(false);
    }
  }

  function onTestConnection() {
    setTesting(true);
    window.setTimeout(() => {
      if (razorpayKeysLookValid(keyId, keySecret)) {
        toast.success("Sandbox format looks valid", "No live Razorpay call was made from this UI.");
      } else {
        toast.error("Invalid Razorpay keys", razorpayKeyIdError(keyId) ?? razorpaySecretError(keySecret) ?? "Check both fields.");
      }
      setTesting(false);
    }, 420);
  }

  async function onStep3(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      saveOnboardingExtras({
        company_size: companySize,
        monthly_volume: monthlyVolume,
        ai_explanations: aiExplanations,
      });
      saveAiStepDone();
      if (geminiKey.trim()) {
        await updateGemini({ api_key: geminiKey.trim() });
      }
      await updateNotifications({
        notify_email_recovery: notifyRecovery,
        notify_email_digest: notifyDigest,
        notify_webhook_failures: notifyWebhook,
      });
      setStep(4);
    } catch (err) {
      setError(authErrorMessage(err, "Could not save AI settings"));
    } finally {
      setPending(false);
    }
  }

  async function onFinish() {
    setPending(true);
    setError(null);
    try {
      await completeWorkspace(workspaceKind);
      await goDashboard();
    } catch (err) {
      setError(authErrorMessage(err, "Could not finish onboarding"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="min-h-screen bg-canvas text-foreground">
      <header className="mx-auto flex max-w-3xl items-center justify-between px-4 py-6">
        <div>
          <p className="text-sm font-semibold text-ai">RecoveryPilot</p>
          <p className="text-xs text-muted">Merchant onboarding</p>
        </div>
        <button type="button" className="text-xs text-muted hover:text-foreground" onClick={() => void logout()}>
          Sign out
        </button>
      </header>
      <main className="mx-auto max-w-3xl px-4 pb-16">
        <div className="mb-3 h-1.5 overflow-hidden rounded-full bg-surface">
          <div
            className="h-full rounded-full bg-gradient-to-r from-ai to-info transition-all duration-300"
            style={{ width: `${(step / 4) * 100}%` }}
            aria-hidden
          />
        </div>
        <ol className="mb-8 grid grid-cols-2 gap-2 md:grid-cols-4" aria-label="Onboarding progress">
          {STEPS.map((label, index) => {
            const n = index + 1;
            const active = n === step;
            const done = n < step;
            return (
              <li
                key={label}
                className={`rounded-xl border px-3 py-2 text-xs ${
                  active
                    ? "border-ai bg-ai-muted text-foreground"
                    : done
                      ? "border-recovered/40 text-recovered"
                      : "border-border text-muted"
                }`}
              >
                <span className="font-medium">0{n}</span> {label}
              </li>
            );
          })}
        </ol>
        <div className="rounded-2xl border border-border bg-surface p-6 shadow-[var(--shadow-card)]">
          {error ? <p className="mb-4 text-sm text-blocked">{error}</p> : null}
          <AnimatePresence mode="wait">
            {step === 1 ? (
              <motion.form
                key="step-1"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                className="space-y-3"
                onSubmit={(event) => void onStep1(event)}
              >
                <h1 className="text-lg font-semibold">Merchant Profile</h1>
                <p className="text-sm text-muted">Name the tenant recovery cases will belong to.</p>
                <label className="block text-sm">
                  Merchant name
                  <input
                    required
                    value={merchantName}
                    onChange={(event) => setMerchantName(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm"
                  />
                </label>
                <fieldset>
                  <legend className="text-sm">Business type</legend>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {(types.length ? types : ["Fitness & Wellness", "SaaS", "Other"]).map((item) => (
                      <label
                        key={item}
                        className={`cursor-pointer rounded-xl border px-3 py-2 text-sm ${
                          businessType === item ? "border-ai bg-ai-muted" : "border-border"
                        }`}
                      >
                        <input
                          type="radio"
                          className="sr-only"
                          checked={businessType === item}
                          onChange={() => setBusinessType(item)}
                        />
                        {item}
                      </label>
                    ))}
                  </div>
                </fieldset>
                <label className="block text-sm">
                  Company size
                  <select
                    value={companySize}
                    onChange={(event) => setCompanySize(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm"
                  >
                    {COMPANY_SIZES.map((size) => (
                      <option key={size} value={size}>
                        {size} employees
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm">
                  Monthly subscription volume
                  <select
                    value={monthlyVolume}
                    onChange={(event) => setMonthlyVolume(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm"
                  >
                    {MONTHLY_VOLUMES.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <AuthSubmitButton
                  pending={pending}
                  idleLabel="Continue"
                  pendingLabel="Saving…"
                  className="rp-btn-ripple inline-flex items-center justify-center gap-2 rounded-lg bg-ai px-4 py-2 text-sm font-medium text-canvas disabled:opacity-60"
                />
              </motion.form>
            ) : null}
            {step === 2 ? (
              <motion.form
                key="step-2"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                className="space-y-3"
                onSubmit={(event) => void onStep2(event)}
              >
                <h1 className="text-lg font-semibold">Razorpay Sandbox</h1>
                <p className="text-sm text-muted">
                  Keys stay on the merchant settings row. This UI never captures a live payment.
                </p>
                <label className="block text-sm">
                  Key ID
                  <input
                    required
                    value={keyId}
                    onChange={(event) => setKeyId(event.target.value)}
                    placeholder="rzp_test_…"
                    className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 font-mono text-sm"
                    aria-invalid={Boolean(keyId && razorpayKeyIdError(keyId))}
                  />
                </label>
                <PasswordField
                  label="Key Secret"
                  value={keySecret}
                  autoComplete="off"
                  disabled={pending}
                  required
                  onChange={setKeySecret}
                />
                <PasswordField
                  label="Webhook secret"
                  value={webhookSecret}
                  autoComplete="off"
                  disabled={pending}
                  onChange={setWebhookSecret}
                />
                <div className="flex flex-wrap gap-2">
                  <button type="button" className="text-sm text-muted" onClick={() => setStep(1)}>
                    Back
                  </button>
                  <button
                    type="button"
                    className="rp-btn-ripple rounded-lg border border-border px-3 py-2 text-sm"
                    disabled={testing}
                    onClick={onTestConnection}
                  >
                    {testing ? "Testing…" : "Test Connection"}
                  </button>
                  <AuthSubmitButton
                    pending={pending}
                    idleLabel="Continue"
                    pendingLabel="Saving…"
                    className="rp-btn-ripple inline-flex items-center justify-center gap-2 rounded-lg bg-ai px-4 py-2 text-sm font-medium text-canvas disabled:opacity-60"
                  />
                </div>
              </motion.form>
            ) : null}
            {step === 3 ? (
              <motion.form
                key="step-3"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                className="space-y-3"
                onSubmit={(event) => void onStep3(event)}
              >
                <h1 className="text-lg font-semibold">AI Configuration</h1>
                <p className="text-sm text-muted">Gemini is optional. Diagnosis still falls back to deterministic copy.</p>
                <PasswordField
                  label="Gemini API key (optional)"
                  value={geminiKey}
                  autoComplete="off"
                  disabled={pending}
                  onChange={setGeminiKey}
                />
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={aiExplanations}
                    onChange={(event) => setAiExplanations(event.target.checked)}
                  />
                  Enable AI explanations in the case drawer
                </label>
                <p className="text-xs font-medium text-muted">Notification preferences</p>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={notifyRecovery} onChange={(event) => setNotifyRecovery(event.target.checked)} />
                  Email when a recovery succeeds
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={notifyDigest} onChange={(event) => setNotifyDigest(event.target.checked)} />
                  Weekly merchant digest
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" checked={notifyWebhook} onChange={(event) => setNotifyWebhook(event.target.checked)} />
                  Alert on webhook signature failures
                </label>
                <div className="flex gap-2">
                  <button type="button" className="text-sm text-muted" onClick={() => setStep(2)}>
                    Back
                  </button>
                  <AuthSubmitButton
                    pending={pending}
                    idleLabel="Continue"
                    pendingLabel="Saving…"
                    className="rp-btn-ripple inline-flex items-center justify-center gap-2 rounded-lg bg-ai px-4 py-2 text-sm font-medium text-canvas disabled:opacity-60"
                  />
                </div>
              </motion.form>
            ) : null}
            {step === 4 ? (
              <motion.div
                key="step-4"
                initial={{ opacity: 0, x: 16 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -16 }}
                className="space-y-4"
              >
                <h1 className="text-lg font-semibold">Workspace Choice</h1>
                <p className="text-sm text-muted">Load FitLife seed-42 or start with an empty tenant.</p>
                <div className="grid gap-3 md:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => setWorkspaceKind("demo")}
                    className={`rounded-xl border p-4 text-left ${
                      workspaceKind === "demo" ? "border-ai bg-ai-muted" : "border-border hover:border-ai"
                    }`}
                  >
                    <p className="font-medium">Load Demo Workspace</p>
                    <p className="mt-1 text-xs text-muted">FitLife seed-42 queue, KPIs, and simulator catalog.</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => setWorkspaceKind("empty")}
                    className={`rounded-xl border p-4 text-left ${
                      workspaceKind === "empty" ? "border-info bg-info-muted" : "border-border hover:border-info"
                    }`}
                  >
                    <p className="font-medium">Start Empty Workspace</p>
                    <p className="mt-1 text-xs text-muted">No customers yet. Charts stay hidden until you import data.</p>
                  </button>
                </div>
                <div className="flex gap-2">
                  <button type="button" className="text-sm text-muted" onClick={() => setStep(3)}>
                    Back
                  </button>
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => void onFinish()}
                    className="rp-btn-ripple inline-flex items-center justify-center gap-2 rounded-lg bg-ai px-4 py-2 text-sm font-medium text-canvas disabled:opacity-60"
                  >
                    {pending ? "Finishing…" : "Finish"}
                  </button>
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}
