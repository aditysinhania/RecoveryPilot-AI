export type WorkspaceKind = "none" | "demo" | "empty";

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  merchant_id: string | null;
  merchant_name: string | null;
  onboarding_completed: boolean;
  onboarding_step: number;
  workspace_kind: WorkspaceKind;
}

export interface TokenPayload {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface AccountSettings {
  merchant_name: string;
  business_category: string;
  email: string;
  phone: string;
  timezone: string;
  razorpay_key_id: string | null;
  razorpay_configured: boolean;
  webhook_configured: boolean;
  gemini_configured: boolean;
  gemini_model: string | null;
  notify_email_recovery: boolean;
  notify_email_digest: boolean;
  notify_webhook_failures: boolean;
  workspace_kind: WorkspaceKind;
  onboarding_completed: boolean;
}

export interface AuthSessionRow {
  id: string;
  created_at: string;
  expires_at: string;
  user_agent: string | null;
  ip_address: string | null;
  current: boolean;
}
