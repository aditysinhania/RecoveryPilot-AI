import { Bell, Search } from "lucide-react";
import { formatRelativeTime } from "@/lib/format";
import type { MerchantOption } from "@/types/dashboard";

interface TopNavbarProps {
  merchants: MerchantOption[];
  merchantId: string;
  onMerchantChange: (id: string) => void;
  environment: string;
  lastSyncedAt: string;
  dataSource: "live" | "simulator";
}

/** Merchant chrome: selector, env, sync, search, notifications, avatar. */
export function TopNavbar({
  merchants,
  merchantId,
  onMerchantChange,
  environment,
  lastSyncedAt,
  dataSource,
}: TopNavbarProps) {
  return (
    <header className="flex h-16 shrink-0 items-center gap-4 border-b border-border bg-canvas-muted/80 px-4 backdrop-blur">
      <label className="sr-only" htmlFor="merchant-select">
        Merchant
      </label>
      <select
        id="merchant-select"
        value={merchantId}
        onChange={(event) => onMerchantChange(event.target.value)}
        className="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-foreground"
      >
        {merchants.map((merchant) => (
          <option key={merchant.id} value={merchant.id}>
            {merchant.merchant_name}
          </option>
        ))}
      </select>
      <span className="rounded-full bg-info-muted px-2.5 py-1 text-[11px] font-medium uppercase tracking-wide text-info">
        {environment}
      </span>
      <span className="hidden text-xs text-muted lg:inline">
        Last sync {formatRelativeTime(lastSyncedAt)} · {dataSource === "live" ? "API" : "Simulator seed 42"}
      </span>
      <div className="ml-auto flex items-center gap-2">
        <label className="relative hidden md:block">
          <span className="sr-only">Search</span>
          <Search className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" size={14} />
          <input
            type="search"
            placeholder="Search cases"
            className="w-56 rounded-lg border border-border bg-surface py-1.5 pl-8 pr-3 text-sm text-foreground placeholder:text-muted"
            aria-label="Search cases"
          />
        </label>
        <button
          type="button"
          className="rounded-lg p-2 text-muted hover:bg-surface-hover hover:text-foreground"
          aria-label="Notifications"
        >
          <Bell size={18} />
        </button>
        <span
          className="flex h-8 w-8 items-center justify-center rounded-full bg-ai-muted text-xs font-semibold text-ai"
          aria-label="Merchant user"
        >
          FG
        </span>
      </div>
    </header>
  );
}
