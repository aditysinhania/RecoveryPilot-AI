import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { PriorityBadge } from "@/components/shared/PriorityBadge";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatPaise, initials, titleCase } from "@/lib/format";
import type { RecoveryCaseDetail } from "@/types/recovery";

interface CaseHeaderProps {
  detail: RecoveryCaseDetail;
}

function CopyableId({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);

  const onCopy = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="flex min-w-0 items-center gap-1.5 text-[11px]">
      <span className="shrink-0 text-muted">{label}</span>
      <span className="min-w-0 truncate font-mono text-zinc-400" title={value}>
        {value}
      </span>
      <button
        type="button"
        className="shrink-0 rounded p-0.5 text-zinc-500 hover:bg-surface-hover hover:text-foreground"
        onClick={() => {
          void onCopy();
        }}
        aria-label={copied ? `${label} copied` : `Copy ${label}`}
      >
        {copied ? <Check size={11} className="text-recovered" /> : <Copy size={11} />}
      </button>
    </div>
  );
}

/** Drawer header: avatar, identity, amount at risk, status, priority, and IDs. */
export function CaseHeader({ detail }: CaseHeaderProps) {
  const plan = detail.subscription?.subscription_name ?? "Membership";
  return (
    <header className="border-b border-border px-4 py-3 sm:px-5 sm:py-4">
      <div className="flex items-start gap-3">
        <span
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-ai-muted text-sm font-semibold text-ai ring-1 ring-ai/30"
          aria-hidden
        >
          {initials(detail.customer.full_name)}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <h2 id="case-drawer-title" className="truncate text-base font-semibold">
              {detail.customer.full_name}
            </h2>
            <StatusBadge status={detail.recovery_status} />
            <PriorityBadge score={detail.priority_score ?? 0} />
          </div>
          <p className="mt-1 text-xs text-muted">
            {titleCase(detail.customer.customer_segment)} · {plan}
          </p>
          <p className="mt-2 text-lg font-semibold tabular-nums text-info">
            {formatPaise(detail.payment.amount)}
            <span className="ml-2 text-xs font-normal text-muted">at risk</span>
          </p>
          <div className="mt-2 space-y-0.5">
            <CopyableId label="Case" value={detail.recovery_case_id} />
            <CopyableId label="Payment" value={detail.payment.id} />
          </div>
        </div>
      </div>
    </header>
  );
}
