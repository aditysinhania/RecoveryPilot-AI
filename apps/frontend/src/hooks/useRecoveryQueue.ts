import { useQuery } from "@tanstack/react-query";
import { fetchRecoveryQueue, type QueueQuery } from "@/services/recoveryQueue";

/** Paginated recovery queue plus filter-aware summary chips. */
export function useRecoveryQueue(query: QueueQuery) {
  return useQuery({
    queryKey: [
      "recovery-queue",
      query.merchantId,
      query.filters,
      query.page,
      query.pageSize,
      query.sortKey,
      query.sortDir,
      query.simulatorOnly ?? false,
      query.emptyWorkspace ?? false,
    ],
    queryFn: () => fetchRecoveryQueue(query),
    staleTime: 20_000,
    retry: 0,
    placeholderData: (previous) => previous,
  });
}
