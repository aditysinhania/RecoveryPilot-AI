import { motion } from "framer-motion";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { TimelineItem } from "@/components/shared/TimelineItem";
import { EmptyState } from "@/components/shared/EmptyState";
import { fadeUp } from "@/lib/motion";
import type { ActivityItem } from "@/types/dashboard";

interface RecentActivityProps {
  items: ActivityItem[];
}

/** Latest execution / audit events as a compact two-column feed. */
export function RecentActivity({ items }: RecentActivityProps) {
  return (
    <motion.section
      {...fadeUp}
      className="rounded-xl border border-border bg-surface p-4 shadow-[var(--shadow-card)]"
    >
      <SectionHeader title="Recent recovery activity" description="Latest executions from the simulator audit trail." />
      {items.length === 0 ? (
        <EmptyState title="No activity" description="Audit events will appear here when the ledger is populated." />
      ) : (
        <ol className="grid gap-2 sm:grid-cols-2">
          {items.map((item, index) => (
            <TimelineItem key={`${item.event_type}-${item.timestamp}-${index}`} item={item} />
          ))}
        </ol>
      )}
    </motion.section>
  );
}
