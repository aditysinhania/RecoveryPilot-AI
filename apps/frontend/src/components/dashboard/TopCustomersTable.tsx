import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { PriorityBadge } from "@/components/shared/PriorityBadge";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { EmptyState } from "@/components/shared/EmptyState";
import { formatPaise, titleCase } from "@/lib/format";
import { fadeUp } from "@/lib/motion";
import type { TopCustomerRow } from "@/types/dashboard";

interface TopCustomersTableProps {
  rows: TopCustomerRow[];
}

/** Top five customers still at risk. Row click opens the recovery-queue drawer. */
export function TopCustomersTable({ rows }: TopCustomersTableProps) {
  const navigate = useNavigate();
  const shown = rows.slice(0, 5);

  return (
    <motion.section
      {...fadeUp}
      className="rounded-xl border border-border bg-surface p-4 shadow-[var(--shadow-card)]"
    >
      <SectionHeader
        title="Top customers at risk"
        description="Highest-priority open recoveries. Open a row to inspect the AI case drawer."
        action={
          <Link
            to="/recovery-queue"
            className="inline-flex items-center gap-1 text-xs font-medium text-info hover:underline"
          >
            View all recovery cases
            <ArrowRight size={14} aria-hidden />
          </Link>
        }
      />
      {shown.length === 0 ? (
        <EmptyState title="No open cases" description="Waiting recoveries will list here." />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wide text-muted">
              <tr>
                <th className="pb-2 font-medium">Customer</th>
                <th className="pb-2 font-medium">Plan</th>
                <th className="pb-2 font-medium">Amount</th>
                <th className="pb-2 font-medium">Diagnosis</th>
                <th className="pb-2 font-medium">Strategy</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 font-medium">Priority</th>
              </tr>
            </thead>
            <tbody>
              {shown.map((row) => (
                <tr
                  key={row.recovery_case_id}
                  tabIndex={0}
                  className="cursor-pointer border-t border-border hover:bg-surface-hover focus-visible:bg-surface-hover"
                  onClick={() => navigate(`/recovery-queue?case=${row.recovery_case_id}`)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      navigate(`/recovery-queue?case=${row.recovery_case_id}`);
                    }
                  }}
                >
                  <td className="py-2">
                    <p className="font-medium text-foreground">{row.customer_name}</p>
                    <p className="text-[11px] text-muted">{titleCase(row.customer_segment)}</p>
                  </td>
                  <td className="py-2 text-muted">{row.plan_name}</td>
                  <td className="py-2 font-medium text-foreground">{formatPaise(row.amount)}</td>
                  <td className="py-2 text-muted">{titleCase(row.diagnosis)}</td>
                  <td className="py-2 text-muted">{row.strategy}</td>
                  <td className="py-2">
                    <StatusBadge status={row.recovery_status} />
                  </td>
                  <td className="py-2">
                    <PriorityBadge score={row.priority_score} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </motion.section>
  );
}
