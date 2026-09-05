import { getData, patchBody, postBody } from "@/lib/api";
import type { AccountSettings, AuthSessionRow } from "@/types/auth";

export async function fetchSettings(): Promise<AccountSettings> {
  return getData<AccountSettings>("/account/settings", 8_000);
}

export async function updateProfile(input: {
  full_name?: string;
  merchant_name?: string;
  phone?: string;
  timezone?: string;
}): Promise<AccountSettings> {
  return patchBody<AccountSettings>("/account/settings/profile", input);
}

export async function updateRazorpay(input: {
  key_id?: string;
  key_secret?: string;
  webhook_secret?: string;
}): Promise<AccountSettings> {
  return patchBody<AccountSettings>("/account/settings/razorpay", input);
}

export async function updateGemini(input: {
  api_key?: string;
  model?: string;
}): Promise<AccountSettings> {
  return patchBody<AccountSettings>("/account/settings/gemini", input);
}

export async function updateNotifications(input: {
  notify_email_recovery?: boolean;
  notify_email_digest?: boolean;
  notify_webhook_failures?: boolean;
}): Promise<AccountSettings> {
  return patchBody<AccountSettings>("/account/settings/notifications", input);
}

export async function changePassword(input: {
  current_password: string;
  new_password: string;
}): Promise<void> {
  await postBody("/account/settings/password", input);
}

export async function fetchSessions(): Promise<AuthSessionRow[]> {
  return getData<AuthSessionRow[]>("/account/sessions", 8_000);
}

export async function revokeAllSessions(): Promise<number> {
  const data = await postBody<{ revoked: number }>("/account/sessions/revoke-all", {});
  return data.revoked;
}
