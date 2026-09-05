import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@/auth/AuthProvider";
import { useDemoMode } from "@/demo/DemoContext";
import {
  assembleDashboard,
  emptyDashboardView,
  fetchLiveDashboard,
  fetchMerchants,
  FITLIFE_LIST_ID,
  SNAPSHOT,
} from "@/services/dashboard";
import type { MerchantOption, TrendRange } from "@/types/dashboard";

const FITLIFE_MERCHANT: MerchantOption = {
  id: FITLIFE_LIST_ID,
  merchant_name: SNAPSHOT.merchant.merchant_name,
  business_category: SNAPSHOT.merchant.business_category,
  timezone: SNAPSHOT.merchant.timezone,
};

/** Load merchants, then compose the live + simulator dashboard view. */
export function useMerchantDashboard() {
  const { user } = useAuth();
  const { isDemo } = useDemoMode();
  const emptyId =
    !isDemo && user?.workspace_kind === "empty" && user.merchant_id ? user.merchant_id : null;
  const [merchantId, setMerchantId] = useState(isDemo ? FITLIFE_LIST_ID : (emptyId ?? FITLIFE_LIST_ID));
  const [trendRange, setTrendRange] = useState<TrendRange>(30);

  useEffect(() => {
    if (isDemo) {
      setMerchantId(FITLIFE_LIST_ID);
    } else if (emptyId) {
      setMerchantId(emptyId);
    }
  }, [emptyId, isDemo]);

  const merchantsQuery = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
    staleTime: 60_000,
    enabled: !isDemo,
  });

  const merchants: MerchantOption[] = isDemo
    ? [FITLIFE_MERCHANT]
    : (merchantsQuery.data ?? [FITLIFE_MERCHANT]);
  const withWorkspace =
    emptyId && user
      ? [
          {
            id: emptyId,
            merchant_name: user.merchant_name ?? "Your workspace",
            business_category: "Merchant",
            timezone: "Asia/Kolkata",
          },
          ...merchants.filter((item) => item.id !== emptyId),
        ]
      : merchants;

  const selected =
    withWorkspace.find((item) => item.id === merchantId) ?? withWorkspace[0] ?? FITLIFE_MERCHANT;
  const emptyWorkspace = Boolean(emptyId && selected.id === emptyId);

  const dashboardQuery = useQuery({
    queryKey: ["merchant-dashboard", selected.id],
    queryFn: () => fetchLiveDashboard(selected.id),
    staleTime: 30_000,
    enabled: !isDemo && !emptyWorkspace,
  });

  const view = useMemo(() => {
    if (emptyWorkspace) {
      return emptyDashboardView(selected, new Date().toISOString());
    }
    if (isDemo) {
      return assembleDashboard(FITLIFE_MERCHANT, null, SNAPSHOT.as_of);
    }
    return assembleDashboard(
      selected,
      dashboardQuery.data ?? null,
      dashboardQuery.dataUpdatedAt
        ? new Date(dashboardQuery.dataUpdatedAt).toISOString()
        : SNAPSHOT.as_of,
    );
  }, [dashboardQuery.data, dashboardQuery.dataUpdatedAt, emptyWorkspace, isDemo, selected]);

  const trend = useMemo(() => {
    const points = view.trend;
    return points.slice(-trendRange);
  }, [view.trend, trendRange]);

  return {
    merchantId: selected.id,
    setMerchantId,
    merchants: withWorkspace,
    trendRange,
    setTrendRange,
    fullTrend: view.trend,
    view: { ...view, trend },
    emptyWorkspace,
    isDemo,
    isLoading: !isDemo && !emptyWorkspace && merchantsQuery.isPending && !merchantsQuery.data,
    isError: !isDemo && !emptyWorkspace && dashboardQuery.isError && !dashboardQuery.data,
    error: dashboardQuery.error,
    refetch: dashboardQuery.refetch,
    isFetching: dashboardQuery.isFetching,
  };
}
