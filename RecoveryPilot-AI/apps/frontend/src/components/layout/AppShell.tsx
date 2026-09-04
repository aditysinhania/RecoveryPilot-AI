import { useState, type ReactNode } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopNavbar } from "@/components/layout/TopNavbar";
import type { MerchantOption } from "@/types/dashboard";

interface AppShellProps {
  children: ReactNode;
  merchants: MerchantOption[];
  merchantId: string;
  onMerchantChange: (id: string) => void;
  environment: string;
  lastSyncedAt: string;
  dataSource: "live" | "simulator";
}

/** Desktop-first shell: sidebar + top bar + main. */
export function AppShell({
  children,
  merchants,
  merchantId,
  onMerchantChange,
  environment,
  lastSyncedAt,
  dataSource,
}: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div className="flex h-screen overflow-hidden bg-canvas text-foreground">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-3 focus:py-2"
      >
        Skip to dashboard
      </a>
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <TopNavbar
          merchants={merchants}
          merchantId={merchantId}
          onMerchantChange={onMerchantChange}
          environment={environment}
          lastSyncedAt={lastSyncedAt}
          dataSource={dataSource}
        />
        <main id="main-content" className="min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto p-3 lg:p-5">
          {children}
        </main>
      </div>
    </div>
  );
}
