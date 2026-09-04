import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import {
  assembleDashboard,
  fetchLiveDashboard,
  fetchMerchants,
  FITLIFE_LIST_ID,
  SNAPSHOT,
} from "@/services/dashboard";
import type { MerchantOption, TrendRange } from "@/types/dashboard";

/** Load merchants, then compose the live + simulator dashboard view. */
export function useMerchantDashboard() {
  const [merchantId, setMerchantId] = useState(FITLIFE_LIST_ID);
  const [trendRange, setTrendRange] = useState<TrendRange>(30);

  const merchantsQuery = useQuery({
    queryKey: ["merchants"],
    queryFn: fetchMerchants,
    staleTime: 60_000,
  });

  const merchants: MerchantOption[] = merchantsQuery.data ?? [
    {
      id: FITLIFE_LIST_ID,
      merchant_name: SNAPSHOT.merchant.merchant_name,
      business_category: SNAPSHOT.merchant.business_category,
      timezone: SNAPSHOT.merchant.timezone,
    },
  ];

  const selected =
    merchants.find((item) => item.id === merchantId) ?? merchants[0];

  const dashboardQuery = useQuery({
    queryKey: ["merchant-dashboard", selected.id],
    queryFn: () => fetchLiveDashboard(selected.id),
    staleTime: 30_000,
  });

  const view = useMemo(
    () =>
      assembleDashboard(
        selected,
        dashboardQuery.data ?? null,
        dashboardQuery.dataUpdatedAt
          ? new Date(dashboardQuery.dataUpdatedAt).toISOString()
          : SNAPSHOT.as_of,
      ),
    [dashboardQuery.data, dashboardQuery.dataUpdatedAt, selected],
  );

  const trend = useMemo(() => {
    const points = view.trend;
    return points.slice(-trendRange);
  }, [view.trend, trendRange]);

  return {
    merchantId: selected.id,
    setMerchantId,
    merchants,
    trendRange,
    setTrendRange,
    fullTrend: view.trend,
    view: { ...view, trend },
    isLoading: merchantsQuery.isPending && !merchantsQuery.data,
    isError: dashboardQuery.isError && !dashboardQuery.data,
    error: dashboardQuery.error,
    refetch: dashboardQuery.refetch,
    isFetching: dashboardQuery.isFetching,
  };
}
