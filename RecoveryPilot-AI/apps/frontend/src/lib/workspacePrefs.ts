const PROFILE_KEY = "rp_onboarding_profile";
const AI_STEP_KEY = "rp_onboarding_ai_done";
const TOUR_KEY = "rp_product_tour_v1";
const AVATAR_KEY = "rp_profile_avatar";

export interface OnboardingProfileExtras {
  company_size: string;
  monthly_volume: string;
  ai_explanations: boolean;
}

const DEFAULT_EXTRAS: OnboardingProfileExtras = {
  company_size: "11-50",
  monthly_volume: "50k-2L",
  ai_explanations: true,
};

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    return { ...fallback, ...(JSON.parse(raw) as T) };
  } catch {
    return fallback;
  }
}

/** Extra onboarding fields that are not part of the backend schema. */
export function loadOnboardingExtras(): OnboardingProfileExtras {
  return readJson(PROFILE_KEY, DEFAULT_EXTRAS);
}

/** Persist company size, volume, and AI-explanation preference locally. */
export function saveOnboardingExtras(next: OnboardingProfileExtras): void {
  localStorage.setItem(PROFILE_KEY, JSON.stringify(next));
}

/** Whether the frontend-only AI config step already ran for this browser. */
export function loadAiStepDone(): boolean {
  return localStorage.getItem(AI_STEP_KEY) === "1";
}

/** Mark the AI configuration wizard step complete. */
export function saveAiStepDone(): void {
  localStorage.setItem(AI_STEP_KEY, "1");
}

/** Guided tour completion flag. */
export function isTourComplete(): boolean {
  return localStorage.getItem(TOUR_KEY) === "done";
}

/** Persist that the operator finished or skipped the product tour. */
export function markTourComplete(): void {
  localStorage.setItem(TOUR_KEY, "done");
}

/** Optional data-URL avatar stored only in this browser. */
export function loadAvatarDataUrl(): string | null {
  return localStorage.getItem(AVATAR_KEY);
}

/** Save a local avatar preview. Does not upload to the API. */
export function saveAvatarDataUrl(value: string | null): void {
  if (!value) {
    localStorage.removeItem(AVATAR_KEY);
    return;
  }
  localStorage.setItem(AVATAR_KEY, value);
}

export const COMPANY_SIZES = ["1-10", "11-50", "51-200", "201-500", "500+"] as const;

export const MONTHLY_VOLUMES = [
  { id: "<10k", label: "Under ₹10k" },
  { id: "10k-50k", label: "₹10k – ₹50k" },
  { id: "50k-2L", label: "₹50k – ₹2L" },
  { id: "2L-10L", label: "₹2L – ₹10L" },
  { id: "10L+", label: "₹10L+" },
] as const;
