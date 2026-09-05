import { FlaskConical } from "lucide-react";
import { DemoBadge } from "@/demo/DemoBadge";

/** Persistent demo workspace banner. Shown only on `/demo`. */
export function DemoBanner() {
  return (
    <div
      className="flex shrink-0 items-center justify-center gap-2 border-b border-ai/30 bg-ai-muted/70 px-3 py-1.5 text-center"
      role="status"
    >
      <FlaskConical size={13} className="text-ai" aria-hidden />
      <p className="text-[11px] text-foreground">
        Demo Workspace — No real Razorpay calls. Powered by simulator seed-42.
      </p>
      <DemoBadge compact />
    </div>
  );
}
