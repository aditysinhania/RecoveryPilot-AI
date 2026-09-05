import { CalendarClock, CircleSlash, Link2, Loader, RotateCw, Timer, TriangleAlert } from "lucide-react";
import { StatCard } from "@/components/shared/StatCard";
import type { DashboardView } from "@/types/dashboard";

interface OrchestratorKpiRowProps {
  orchestrator: DashboardView["orchestrator"];
}

/** Phase 9B scheduler, delivery, and queue KPIs. */
export function OrchestratorKpiRow({ orchestrator }: OrchestratorKpiRowProps) {
  const queue = orchestrator.scheduler_queue ?? {
    scheduled: orchestrator.active_scheduler_queue,
    running: 0,
    delayed: 0,
    dead_letter: 0,
  };
  return (
    <div className="space-y-3">
      <section aria-label="Action orchestrator" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Scheduled actions today"
          value={orchestrator.scheduled_actions_today}
          format={(n) => String(Math.round(n))}
          tone="info"
          icon={<CalendarClock size={16} />}
        />
        <StatCard
          label="Payment links sent"
          value={orchestrator.payment_links_sent}
          format={(n) => String(Math.round(n))}
          tone="info"
          icon={<Link2 size={16} />}
        />
        <StatCard
          label="Successful retries"
          value={orchestrator.successful_retries}
          format={(n) => String(Math.round(n))}
          tone="recovered"
          icon={<RotateCw size={16} />}
        />
        <StatCard
          label="Failed deliveries"
          value={orchestrator.failed_deliveries}
          format={(n) => String(Math.round(n))}
          tone="blocked"
          icon={<TriangleAlert size={16} />}
        />
      </section>
      <section aria-label="Scheduler queue" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Scheduler scheduled"
          value={queue.scheduled}
          format={(n) => String(Math.round(n))}
          hint="Waiting for run_at"
          tone="info"
          icon={<CalendarClock size={16} />}
        />
        <StatCard
          label="Scheduler running"
          value={queue.running}
          format={(n) => String(Math.round(n))}
          hint="Claimed by a tick"
          tone="waiting"
          icon={<Loader size={16} />}
        />
        <StatCard
          label="Scheduler delayed"
          value={queue.delayed}
          format={(n) => String(Math.round(n))}
          hint="Overdue, not yet started"
          tone="waiting"
          icon={<Timer size={16} />}
        />
        <StatCard
          label="Scheduler dead-letter"
          value={queue.dead_letter}
          format={(n) => String(Math.round(n))}
          hint="Retry budget exhausted"
          tone="blocked"
          icon={<CircleSlash size={16} />}
        />
      </section>
    </div>
  );
}
