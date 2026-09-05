import { Outlet } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { useMerchantDashboard } from "@/hooks/useMerchantDashboard";

/** Shared chrome for every merchant-ops route. */
export default function DashboardLayout() {
  const dashboard = useMerchantDashboard();
  return (
    <AppShell
      merchants={dashboard.merchants}
      merchantId={dashboard.merchantId}
      onMerchantChange={dashboard.setMerchantId}
      environment={dashboard.view.environment}
      lastSyncedAt={dashboard.view.lastSyncedAt}
      dataSource={dashboard.view.dataSource}
    >
      <Outlet context={dashboard} />
    </AppShell>
  );
}
