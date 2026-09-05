import { motion } from "framer-motion";
import { useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { DemoBanner } from "@/components/layout/DemoBanner";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopNavbar } from "@/components/layout/TopNavbar";
import { useDemoMode } from "@/demo/DemoContext";
import { fadeUp } from "@/lib/motion";
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
  const { isDemo } = useDemoMode();
  const { pathname } = useLocation();

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
        {isDemo ? <DemoBanner /> : null}
        <TopNavbar
          merchants={merchants}
          merchantId={merchantId}
          onMerchantChange={onMerchantChange}
          environment={environment}
          lastSyncedAt={lastSyncedAt}
          dataSource={dataSource}
        />
        <main id="main-content" className="min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto p-3 lg:p-5">
          <motion.div key={pathname} {...fadeUp}>
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  );
}
