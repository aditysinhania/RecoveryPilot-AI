import { useState } from "react";
import { formatDateTime, formatRelativeTime } from "@/lib/format";
import type { ExplanationBlock } from "@/types/recovery";

interface GeminiExplanationCardProps {
  merchant: ExplanationBlock;
  customer: ExplanationBlock;
  compliance: ExplanationBlock;
}

const TABS = [
  { id: "merchant", label: "Merchant" },
  { id: "customer", label: "Customer" },
  { id: "compliance", label: "Compliance" },
] as const;

type TabId = (typeof TABS)[number]["id"];

/** Merchant / customer / compliance copy. Gemini is never called from this UI. */
export function GeminiExplanationCard({ merchant, customer, compliance }: GeminiExplanationCardProps) {
  const [tab, setTab] = useState<TabId>("merchant");
  const blocks: Record<TabId, ExplanationBlock> = { merchant, customer, compliance };
  const item = blocks[tab];
  return (
    <section className="rounded-xl border border-border bg-surface-raised p-4" aria-labelledby="gemini-heading">
      <h3 id="gemini-heading" className="text-[11px] font-semibold uppercase tracking-wide text-ai">
        Gemini explanation
      </h3>
      <div className="mt-2 flex gap-1 rounded-lg bg-canvas p-0.5" role="tablist" aria-label="Explanation audience">
        {TABS.map((entry) => {
          const selected = tab === entry.id;
          return (
            <button
              key={entry.id}
              type="button"
              role="tab"
              aria-selected={selected}
              id={`gemini-tab-${entry.id}`}
              className={`flex-1 rounded-md px-2 py-1.5 text-[11px] font-medium ${
                selected ? "bg-surface-raised text-foreground shadow-sm" : "text-muted hover:text-foreground"
              }`}
              onClick={() => setTab(entry.id)}
            >
              {entry.label}
            </button>
          );
        })}
      </div>
      <article
        role="tabpanel"
        aria-labelledby={`gemini-tab-${tab}`}
        className="mt-3 rounded-lg bg-surface p-3"
      >
        <div className="flex flex-wrap items-center gap-1.5">
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
              item.source === "gemini" ? "bg-ai-muted text-ai" : "bg-zinc-800 text-muted"
            }`}
          >
            {item.source === "gemini" ? "Gemini" : "Fallback"}
          </span>
          {item.cached ? (
            <span className="rounded-full bg-info-muted px-2 py-0.5 text-[10px] font-medium text-info">Cached</span>
          ) : null}
          <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-[10px] text-muted">{item.prompt_version}</span>
          <time className="text-[10px] text-zinc-500" dateTime={item.generated_at} title={formatDateTime(item.generated_at)}>
            {formatRelativeTime(item.generated_at)}
          </time>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-foreground">{item.body}</p>
        <p className="mt-2 text-[11px] text-zinc-500">{formatDateTime(item.generated_at)}</p>
      </article>
    </section>
  );
}
