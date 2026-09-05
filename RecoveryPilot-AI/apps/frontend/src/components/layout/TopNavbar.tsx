import { Bell, Search } from "lucide-react";
import { ProfileMenu } from "@/components/layout/ProfileMenu";
import { WorkspaceSwitcher } from "@/components/layout/WorkspaceSwitcher";
import { DemoBadge } from "@/demo/DemoBadge";
import { useDemoMode } from "@/demo/DemoContext";
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
  const { isDemo } = useDemoMode();

  return (
    <header className="flex h-16 shrink-0 items-center gap-4 border-b border-border bg-canvas-muted/80 px-4 backdrop-blur">
      <WorkspaceSwitcher
        merchants={merchants}
        merchantId={merchantId}
        onMerchantChange={onMerchantChange}
        forceDemoBadge={isDemo}
      />
      {isDemo ? <DemoBadge /> : null}
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
        <ProfileMenu />
      </div>
    </header>
  );
}
