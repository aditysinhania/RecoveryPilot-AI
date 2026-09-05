/** Client-side Razorpay key id check. Does not call Razorpay. */
export function razorpayKeyIdError(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return "Key ID is required.";
  }
  if (!/^rzp_(test|live)_[A-Za-z0-9]{8,}$/.test(trimmed)) {
    return "Use a Razorpay key id such as rzp_test_…";
  }
  return null;
}

/** Client-side secret length check. Secrets are never logged. */
export function razorpaySecretError(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return "Key secret is required.";
  }
  if (trimmed.length < 16) {
    return "Key secret looks too short.";
  }
  return null;
}

/** True when both Sandbox fields look like Razorpay test credentials. */
export function razorpayKeysLookValid(keyId: string, keySecret: string): boolean {
  return razorpayKeyIdError(keyId) === null && razorpaySecretError(keySecret) === null;
}
