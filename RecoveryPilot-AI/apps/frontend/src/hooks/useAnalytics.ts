import { useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useRecoveryQueue } from "@/hooks/useRecoveryQueue";
import { useMerchantDashboard } from "@/hooks/useMerchantDashboard";
import { EMPTY_FILTERS } from "@/lib/recoveryMap";
import { SNAPSHOT_QUEUE } from "@/data/fitlifeQueue";
import { assembleAnalytics } from "@/services/analytics";
import type { AnalyticsRange } from "@/types/analytics";

type LayoutContext = ReturnType<typeof useMerchantDashboard>;

/** Compose dashboard metrics + a wide queue page into an analytics view. */
export function useAnalytics() {
  const ctx = useOutletContext<LayoutContext>();
  const [range, setRange] = useState<AnalyticsRange>(30);
  const queueQuery = useRecoveryQueue({
    merchantId: ctx.merchantId,
    filters: { ...EMPTY_FILTERS, merchantId: ctx.merchantId },
    page: 1,
    pageSize: 100,
    sortKey: "amount",
    sortDir: "desc",
  });
  const rows = queueQuery.data?.page.items ?? SNAPSHOT_QUEUE;
  const model = useMemo(
    () => assembleAnalytics(ctx.view, rows, ctx.fullTrend, range),
    [ctx.view, ctx.fullTrend, rows, range],
  );
  return {
    range,
    setRange,
    model,
    isLoading: ctx.isLoading,
    isError: ctx.isError || queueQuery.isError,
    isFetching: ctx.isFetching || queueQuery.isFetching,
    refetch: (): void => {
      void ctx.refetch();
      void queueQuery.refetch();
    },
  };
}
