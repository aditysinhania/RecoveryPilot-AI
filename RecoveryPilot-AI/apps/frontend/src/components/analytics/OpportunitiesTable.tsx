import { Link } from "react-router-dom";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { ChartCard } from "@/components/shared/ChartCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatPaise } from "@/lib/format";
import type { OpportunityRow } from "@/types/analytics";

interface OpportunitiesTableProps {
  rows: OpportunityRow[];
}

/** Highest expected recovered value among still-open queue cases. */
export function OpportunitiesTable({ rows }: OpportunitiesTableProps) {
  return (
    <ChartCard
      title="Top recovery opportunities"
      description="Open queue cases ranked by amount × display recovery probability."
    >
      {rows.length === 0 ? (
        <EmptyState title="No open opportunities" description="Nothing in the waiting set for this window." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full table-fixed text-left text-xs">
            <thead className="text-[11px] uppercase tracking-wide text-muted">
              <tr>
                <th className="w-[28%] pb-2 font-medium">Customer</th>
                <th className="w-[18%] pb-2 font-medium">Diagnosis</th>
                <th className="w-[16%] pb-2 font-medium">Amount</th>
                <th className="w-[18%] pb-2 font-medium">Expected</th>
                <th className="w-[20%] pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.recovery_case_id} className="border-t border-border">
                  <td className="truncate py-2 pr-2">
                    <Link
                      className="font-medium text-foreground hover:text-info"
                      to={`/recovery-queue?case=${row.recovery_case_id}`}
                    >
                      {row.customer_name}
                    </Link>
                    <p className="truncate text-[11px] text-muted">{row.plan_name}</p>
                  </td>
                  <td className="truncate py-2 pr-2 text-muted" title={row.diagnosis}>
                    {row.diagnosis}
                  </td>
                  <td className="py-2 pr-2 tabular-nums">{formatPaise(row.amount)}</td>
                  <td className="py-2 pr-2 tabular-nums text-recovered">{formatPaise(row.expected_paise)}</td>
                  <td className="py-2">
                    <StatusBadge status={row.recovery_status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </ChartCard>
  );
}
