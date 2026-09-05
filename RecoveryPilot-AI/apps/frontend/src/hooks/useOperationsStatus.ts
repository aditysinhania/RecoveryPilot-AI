import { useQuery } from "@tanstack/react-query";
import { fetchOpsStatus } from "@/services/operations";

/** Poll the operations snapshot every 15s. */
export function useOperationsStatus() {
  return useQuery({
    queryKey: ["ops-status"],
    queryFn: fetchOpsStatus,
    refetchInterval: 15_000,
    staleTime: 5_000,
  });
}
