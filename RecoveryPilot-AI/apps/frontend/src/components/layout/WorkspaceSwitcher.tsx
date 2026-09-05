import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronsUpDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { DemoBadge } from "@/demo/DemoBadge";
import { FITLIFE_LIST_ID } from "@/services/dashboard";
import type { MerchantOption } from "@/types/dashboard";

interface WorkspaceSwitcherProps {
  merchants: MerchantOption[];
  merchantId: string;
  onMerchantChange: (id: string) => void;
  forceDemoBadge?: boolean;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
  }
  return (parts[0] ?? "RP").slice(0, 2).toUpperCase();
}

function isDemoMerchant(id: string, force: boolean): boolean {
  return force || id === FITLIFE_LIST_ID;
}

/** Animated merchant workspace picker with industry and DEMO badges. */
export function WorkspaceSwitcher({
  merchants,
  merchantId,
  onMerchantChange,
  forceDemoBadge = false,
}: WorkspaceSwitcherProps) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const selected = merchants.find((item) => item.id === merchantId) ?? merchants[0];

  useEffect(() => {
    function onDoc(event: MouseEvent) {
      if (root.current && !root.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  if (!selected) {
    return null;
  }

  return (
    <div className="relative min-w-0" ref={root}>
      <button
        type="button"
        className="flex max-w-[min(100%,18rem)] items-center gap-2 rounded-xl border border-border bg-surface px-2 py-1.5 text-left hover:border-ai/40"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label="Switch workspace"
        onClick={() => setOpen((value) => !value)}
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-ai-muted text-[10px] font-semibold text-ai">
          {initials(selected.merchant_name)}
        </span>
        <span className="min-w-0 flex-1">
          <AnimatePresence mode="wait">
            <motion.span
              key={selected.id}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              className="block truncate text-sm font-medium"
            >
              {selected.merchant_name}
            </motion.span>
          </AnimatePresence>
          <span className="mt-0.5 flex items-center gap-1">
            <span className="truncate text-[10px] text-muted">{selected.business_category}</span>
            {isDemoMerchant(selected.id, forceDemoBadge) ? <DemoBadge compact /> : null}
          </span>
        </span>
        <ChevronsUpDown size={14} className="shrink-0 text-muted" aria-hidden />
      </button>
      {open ? (
        <ul
          role="listbox"
          className="absolute left-0 z-40 mt-2 w-72 overflow-hidden rounded-xl border border-border bg-surface p-1 shadow-[var(--shadow-card)]"
        >
          {merchants.map((merchant) => {
            const active = merchant.id === selected.id;
            const demo = isDemoMerchant(merchant.id, forceDemoBadge);
            return (
              <li key={merchant.id} role="option" aria-selected={active}>
                <button
                  type="button"
                  className={`flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left hover:bg-surface-hover ${
                    active ? "bg-surface-hover" : ""
                  }`}
                  onClick={() => {
                    onMerchantChange(merchant.id);
                    setOpen(false);
                  }}
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-ai-muted text-[11px] font-semibold text-ai">
                    {initials(merchant.merchant_name)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm">{merchant.merchant_name}</span>
                    <span className="mt-0.5 flex items-center gap-1">
                      <span className="rounded-full bg-info-muted px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-info">
                        {merchant.business_category}
                      </span>
                      {demo ? <DemoBadge compact /> : null}
                    </span>
                  </span>
                  {active ? <Check size={14} className="text-ai" aria-hidden /> : null}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
