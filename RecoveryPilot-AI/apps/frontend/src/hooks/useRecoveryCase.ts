import { useQuery } from "@tanstack/react-query";
import { fetchRecoveryCase } from "@/services/recoveryQueue";

/** Lazy case drawer fetch, cached by recovery_case_id. */
export function useRecoveryCase(recoveryCaseId: string | null) {
  return useQuery({
    queryKey: ["recovery-case", recoveryCaseId],
    queryFn: () => fetchRecoveryCase(recoveryCaseId as string),
    enabled: Boolean(recoveryCaseId),
    staleTime: 15_000,
    refetchInterval: recoveryCaseId ? 5_000 : false,
    retry: 0,
  });
}
