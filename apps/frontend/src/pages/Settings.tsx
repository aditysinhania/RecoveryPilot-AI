import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/auth/AuthProvider";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { useDemoMode } from "@/demo/DemoContext";
import { DashboardApiError } from "@/lib/api";
import { loadAvatarDataUrl, saveAvatarDataUrl } from "@/lib/workspacePrefs";
import { razorpayKeyIdError, razorpayKeysLookValid, razorpaySecretError } from "@/lib/razorpayKeys";
import {
  changePassword,
  fetchSessions,
  fetchSettings,
  revokeAllSessions,
  updateGemini,
  updateNotifications,
  updateProfile,
  updateRazorpay,
} from "@/services/account";
import { useToast } from "@/toast/ToastProvider";
import type { AccountSettings, AuthSessionRow } from "@/types/auth";

type TabId = "profile" | "razorpay" | "gemini" | "notifications" | "security" | "theme" | "integrations";

const TABS: { id: TabId; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "razorpay", label: "API keys" },
  { id: "gemini", label: "Gemini" },
  { id: "notifications", label: "Notifications" },
  { id: "security", label: "Security" },
  { id: "theme", label: "Theme" },
  { id: "integrations", label: "Integrations" },
];

/** Merchant settings: profile, vendors, notifications, security. */
export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const { isDemo } = useDemoMode();
  const toast = useToast();
  const [tab, setTab] = useState<TabId>("profile");
  const [settings, setSettings] = useState<AccountSettings | null>(null);
  const [sessions, setSessions] = useState<AuthSessionRow[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [avatar, setAvatar] = useState<string | null>(() => loadAvatarDataUrl());

  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [merchantName, setMerchantName] = useState("");
  const [phone, setPhone] = useState("");
  const [timezone, setTimezone] = useState("Asia/Kolkata");
  const [keyId, setKeyId] = useState("");
  const [keySecret, setKeySecret] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("gemini-2.5-flash");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  useEffect(() => {
    if (isDemo && !user) {
      return;
    }
    void (async () => {
      try {
        const snapshot = await fetchSettings();
        setSettings(snapshot);
        setMerchantName(snapshot.merchant_name);
        setPhone(snapshot.phone);
        setTimezone(snapshot.timezone);
        setGeminiModel(snapshot.gemini_model ?? "gemini-2.5-flash");
        setSessions(await fetchSessions());
      } catch (err) {
        setError(err instanceof DashboardApiError ? err.message : "Could not load settings");
      }
    })();
  }, [isDemo, user]);

  function flash(ok: string) {
    setMessage(ok);
    setError(null);
    toast.success(ok);
  }

  async function onProfile(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    try {
      const next = await updateProfile({
        full_name: fullName,
        merchant_name: merchantName,
        phone,
        timezone,
      });
      setSettings(next);
      await refreshUser();
      flash("Profile saved");
    } catch (err) {
      setError(err instanceof DashboardApiError ? err.message : "Save failed");
    } finally {
      setPending(false);
    }
  }

  async function onRazorpay(event: FormEvent) {
    event.preventDefault();
    if (keyId && razorpayKeyIdError(keyId)) {
      toast.error("Invalid Razorpay keys", razorpayKeyIdError(keyId) ?? "");
      return;
    }
    if (keySecret && razorpaySecretError(keySecret)) {
      toast.error("Invalid Razorpay keys", razorpaySecretError(keySecret) ?? "");
      return;
    }
    setPending(true);
    try {
      const next = await updateRazorpay({
        key_id: keyId || undefined,
        key_secret: keySecret || undefined,
        webhook_secret: webhookSecret || undefined,
      });
      setSettings(next);
      setKeyId("");
      setKeySecret("");
      setWebhookSecret("");
      flash("Razorpay keys updated");
    } catch (err) {
      setError(err instanceof DashboardApiError ? err.message : "Save failed");
    } finally {
      setPending(false);
    }
  }

  async function onGemini(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    try {
      const next = await updateGemini({
        api_key: geminiKey || undefined,
        model: geminiModel,
      });
      setSettings(next);
      setGeminiKey("");
      flash("Gemini settings updated");
    } catch (err) {
      setError(err instanceof DashboardApiError ? err.message : "Save failed");
    } finally {
      setPending(false);
    }
  }

  async function onPassword(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      flash("Password changed");
    } catch (err) {
      setError(err instanceof DashboardApiError ? err.message : "Password change failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-4">
      <SectionHeader
        title="Settings"
        description="Merchant profile, Sandbox keys, Gemini, alerts, and sessions."
      />
      {isDemo && !user ? (
        <p className="rounded-xl border border-ai/30 bg-ai-muted px-3 py-2 text-xs text-ai">
          Demo settings are local-only. Sign up to persist Razorpay and Gemini keys.
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`rounded-full px-3 py-1.5 text-sm ${
              tab === item.id ? "bg-ai-muted text-foreground" : "text-muted hover:bg-surface"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      {message ? <p className="text-sm text-recovered">{message}</p> : null}
      {error ? <p className="text-sm text-blocked">{error}</p> : null}
      <section className="rounded-xl border border-border bg-surface p-4 shadow-[var(--shadow-card)]">
        {tab === "profile" ? (
          <form className="grid max-w-lg gap-3" onSubmit={(event) => void onProfile(event)}>
            <div className="flex items-center gap-3">
              <span className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-full bg-ai-muted text-sm font-semibold text-ai">
                {avatar ? <img src={avatar} alt="" className="h-full w-full object-cover" /> : "RP"}
              </span>
              <label className="text-sm">
                Avatar
                <input
                  type="file"
                  accept="image/*"
                  className="mt-1 block text-xs text-muted"
                  aria-label="Upload avatar placeholder"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (!file) {
                      return;
                    }
                    const reader = new FileReader();
                    reader.onload = () => {
                      const url = String(reader.result);
                      setAvatar(url);
                      saveAvatarDataUrl(url);
                      toast.success("Avatar preview saved", "Stored in this browser only.");
                    };
                    reader.readAsDataURL(file);
                  }}
                />
              </label>
            </div>
            <p className="text-xs text-muted">
              Organization · {settings?.business_category || user?.merchant_name || "RecoveryPilot merchant"} ·{" "}
              {settings?.workspace_kind === "demo" ? "Demo workspace" : "Merchant workspace"}
            </p>
            <label className="text-sm">
              Operator name
              <input
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm">
              Merchant name
              <input
                value={merchantName}
                onChange={(event) => setMerchantName(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm">
              Phone
              <input
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm"
              />
            </label>
            <label className="text-sm">
              Timezone
              <input
                value={timezone}
                onChange={(event) => setTimezone(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm"
              />
            </label>
            <p className="text-xs text-muted">Email {settings?.email ?? user?.email} cannot be changed here.</p>
            <button
              type="submit"
              disabled={pending}
              className="w-fit rounded-lg bg-ai px-4 py-2 text-sm font-medium text-canvas"
            >
              Save profile
            </button>
          </form>
        ) : null}
        {tab === "razorpay" ? (
          <form className="grid max-w-lg gap-3" onSubmit={(event) => void onRazorpay(event)}>
            <p className="text-sm text-muted">
              {settings?.razorpay_configured
                ? `Configured · ${settings.razorpay_key_id ?? "key on file"}`
                : "No Sandbox keys stored yet."}
            </p>
            <label className="text-sm">
              Key id
              <input
                value={keyId}
                onChange={(event) => setKeyId(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 font-mono text-sm"
              />
            </label>
            <label className="text-sm">
              Key secret
              <input
                type="password"
                value={keySecret}
                onChange={(event) => setKeySecret(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 font-mono text-sm"
              />
            </label>
            <label className="text-sm">
              Webhook secret
              <input
                type="password"
                value={webhookSecret}
                onChange={(event) => setWebhookSecret(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 font-mono text-sm"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-lg border border-border px-4 py-2 text-sm"
                onClick={() => {
                  if (razorpayKeysLookValid(keyId, keySecret)) {
                    toast.success("Sandbox format looks valid", "No live Razorpay call was made.");
                  } else {
                    toast.error(
                      "Invalid Razorpay keys",
                      razorpayKeyIdError(keyId) ?? razorpaySecretError(keySecret) ?? "Check both fields.",
                    );
                  }
                }}
              >
                Test Connection
              </button>
              <button
                type="submit"
                disabled={pending}
                className="w-fit rounded-lg bg-ai px-4 py-2 text-sm font-medium text-canvas"
              >
                Save keys
              </button>
            </div>
          </form>
        ) : null}
        {tab === "gemini" ? (
          <form className="grid max-w-lg gap-3" onSubmit={(event) => void onGemini(event)}>
            <p className="text-sm text-muted">
              {settings?.gemini_configured ? "A Gemini key is on file (redacted)." : "Using process env until you save a key."}
            </p>
            <label className="text-sm">
              API key
              <input
                type="password"
                value={geminiKey}
                onChange={(event) => setGeminiKey(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 font-mono text-sm"
              />
            </label>
            <label className="text-sm">
              Model
              <input
                value={geminiModel}
                onChange={(event) => setGeminiModel(event.target.value)}
                className="mt-1 w-full rounded-lg border border-border bg-canvas px-3 py-2 text-sm"
              />
            </label>
            <button
              type="submit"
              disabled={pending}
              className="w-fit rounded-lg bg-ai px-4 py-2 text-sm font-medium text-canvas"
            >
              Save Gemini
            </button>
          </form>
        ) : null}
        {tab === "notifications" && settings ? (
          <div className="grid max-w-lg gap-3 text-sm">
            {(
              [
                ["notify_email_recovery", "Email when a recovery succeeds"],
                ["notify_email_digest", "Weekly merchant digest"],
                ["notify_webhook_failures", "Alert on webhook signature failures"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={settings[key]}
                  onChange={(event) => {
                    const checked = event.target.checked;
                    setSettings({ ...settings, [key]: checked });
                    void updateNotifications({ [key]: checked }).then(setSettings);
                  }}
                />
                {label}
              </label>
            ))}
          </div>
        ) : null}
        {tab === "security" ? (
          <div className="grid gap-6 lg:grid-cols-2">
            <form className="grid gap-3" onSubmit={(event) => void onPassword(event)}>
              <h2 className="text-sm font-semibold">Change password</h2>
              <input
                type="password"
                required
                placeholder="Current password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
                className="rounded-lg border border-border bg-canvas px-3 py-2 text-sm"
              />
              <input
                type="password"
                required
                minLength={8}
                placeholder="New password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                className="rounded-lg border border-border bg-canvas px-3 py-2 text-sm"
              />
              <button
                type="submit"
                disabled={pending}
                className="w-fit rounded-lg bg-ai px-4 py-2 text-sm font-medium text-canvas"
              >
                Update password
              </button>
            </form>
            <div>
              <h2 className="text-sm font-semibold">Sessions</h2>
              <ul className="mt-2 space-y-2 text-xs text-muted">
                {sessions.map((row) => (
                  <li key={row.id} className="rounded-lg border border-border px-3 py-2">
                    {row.current ? "This device · " : ""}
                    {row.user_agent ?? "Unknown client"}
                    <span className="block">{row.ip_address ?? "IP hidden"}</span>
                  </li>
                ))}
              </ul>
              <button
                type="button"
                className="mt-3 text-sm text-blocked hover:underline"
                onClick={() => {
                  void revokeAllSessions().then(() => {
                    flash("All sessions revoked. Sign in again on other devices.");
                    void fetchSessions().then(setSessions);
                  });
                }}
              >
                Sign out all sessions
              </button>
            </div>
          </div>
        ) : null}
        {tab === "theme" ? (
          <div className="grid gap-3 sm:grid-cols-3">
            <p className="sm:col-span-3 text-sm text-muted">
              RecoveryPilot ships a single dark canvas. This preview is visual-only.
            </p>
            {["Canvas", "Surface", "AI glow"].map((name, index) => (
              <div
                key={name}
                className={`rounded-xl border border-border p-4 ${
                  index === 2 ? "bg-ai-muted" : index === 1 ? "bg-surface-raised" : "bg-canvas"
                }`}
              >
                <p className="text-sm font-medium">{name}</p>
                <p className="mt-1 text-xs text-muted">Dark SaaS tokens</p>
              </div>
            ))}
          </div>
        ) : null}
        {tab === "integrations" ? (
          <ul className="grid gap-3 sm:grid-cols-2">
            {[
              { name: "Razorpay Sandbox", status: settings?.razorpay_configured ? "Connected" : "Not connected" },
              { name: "Gemini", status: settings?.gemini_configured ? "Connected" : "Using env fallback" },
              { name: "Simulator seed-42", status: "Available" },
              { name: "WhatsApp (future)", status: "Not wired" },
            ].map((item) => (
              <li key={item.name} className="rounded-xl border border-border px-4 py-3">
                <p className="text-sm font-medium">{item.name}</p>
                <p className="mt-1 text-xs text-muted">{item.status}</p>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </div>
  );
}
