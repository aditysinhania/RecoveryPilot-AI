import { getData, postBody } from "@/lib/api";
import type { AuthUser } from "@/types/auth";

/** Allowed business categories from the API (falls back to a static list). */
export async function fetchBusinessTypes(): Promise<string[]> {
  try {
    return await getData<string[]>("/onboarding/business-types", 6_000);
  } catch {
    return [
      "Fitness & Wellness",
      "EdTech",
      "SaaS",
      "Media",
      "Healthcare",
      "E-commerce",
      "Other",
    ];
  }
}

export async function saveMerchantInfo(input: {
  merchant_name: string;
  phone: string;
  timezone: string;
}): Promise<AuthUser> {
  return postBody<AuthUser>("/onboarding/merchant", input);
}

export async function saveBusinessType(business_type: string): Promise<AuthUser> {
  return postBody<AuthUser>("/onboarding/business", { business_type });
}

export async function saveRazorpayKeys(input: {
  key_id: string;
  key_secret: string;
  webhook_secret: string;
}): Promise<AuthUser> {
  return postBody<AuthUser>("/onboarding/razorpay", input);
}

export async function completeWorkspace(workspace_kind: "demo" | "empty"): Promise<AuthUser> {
  return postBody<AuthUser>("/onboarding/workspace", { workspace_kind });
}
