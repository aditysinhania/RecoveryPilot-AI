import { Loader2 } from "lucide-react";

interface AuthSubmitButtonProps {
  pending: boolean;
  idleLabel: string;
  pendingLabel: string;
  className?: string;
}

/** Primary auth/onboarding submit control with a spinner while the request is in flight. */
export function AuthSubmitButton({
  pending,
  idleLabel,
  pendingLabel,
  className = "inline-flex w-full items-center justify-center gap-2 rounded-lg bg-ai px-3 py-2 text-sm font-medium text-canvas disabled:opacity-60",
}: AuthSubmitButtonProps) {
  return (
    <button type="submit" disabled={pending} aria-busy={pending} className={className}>
      {pending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
      {pending ? pendingLabel : idleLabel}
    </button>
  );
}
