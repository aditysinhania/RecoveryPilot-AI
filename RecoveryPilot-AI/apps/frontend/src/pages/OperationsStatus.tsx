import {
  Activity,
  Database,
  Gauge,
  Link2,
  RotateCw,
  Server,
  Sparkles,
  Timer,
  Webhook,
} from "lucide-react";
import { OpsProbeCard } from "@/components/ops/OpsProbeCard";
import { ErrorState } from "@/components/shared/EmptyState";
import { DashboardSkeleton } from "@/components/shared/LoadingSkeleton";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { StatCard } from "@/components/shared/StatCard";
import { useOperationsStatus } from "@/hooks/useOperationsStatus";
import { FRONTEND_SHA, FRONTEND_VERSION } from "@/services/operations";

function formatMs(value: number): string {
  if (!Number.isFinite(value) || value <= 0) {
    return "—";
  }
  return `${value.toFixed(0)} ms`;
}

/** Production-readiness dashboard: probes, throughput, and build info. */
export default function OperationsStatusPage() {
  const { data, isLoading, isError, isFetching, refetch } = useOperationsStatus();

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (isError || data == null) {
    return (
      <ErrorState
        message="Operations APIs are unavailable. Confirm the backend is running."
        onRetry={() => {
          void refetch();
        }}
      />
    );
  }

  const schedulerDetail = data.scheduler.enabled
    ? `${data.scheduler.scheduled} scheduled · ${data.scheduler.running} running · ${data.scheduler.dead_letter} dead-letter`
    : data.scheduler.detail;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-base font-semibold tracking-tight">Operations Status</h1>
          <p className="text-[11px] text-muted">
            Live probes for API, scheduler, Gemini, Razorpay, and PostgreSQL. Refreshes every 15s.
          </p>
        </div>
        {isFetching ? (
          <p className="text-xs text-muted" aria-live="polite">
            Refreshing…
          </p>
        ) : null}
      </div>

      <section className="rounded-xl border border-border bg-surface p-4 shadow-[var(--shadow-card)]">
        <SectionHeader
          title="Build"
          description={`${data.app_name} · ${data.environment}`}
        />
        <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted">API version</dt>
            <dd className="mt-1 font-medium">{data.version}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted">Backend SHA</dt>
            <dd className="mt-1 truncate font-mono text-xs">{data.build_sha}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted">Frontend</dt>
            <dd className="mt-1 font-medium">{FRONTEND_VERSION}</dd>
          </div>
          <div>
            <dt className="text-[11px] uppercase tracking-wide text-muted">UI SHA</dt>
            <dd className="mt-1 truncate font-mono text-xs">{FRONTEND_SHA}</dd>
          </div>
        </dl>
      </section>

      <SectionHeader title="Dependency health" description="Configuration and connectivity. Gemini and Razorpay probes never call live vendors." />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <OpsProbeCard
          title="API"
          status={data.api.status}
          detail={data.api.detail}
          icon={Server}
          meta={data.environment}
        />
        <OpsProbeCard
          title="Database"
          status={data.database.status}
          detail={data.database.detail}
          icon={Database}
          meta={data.database.mode ?? undefined}
        />
        <OpsProbeCard
          title="Scheduler"
          status={data.scheduler.status}
          detail={schedulerDetail}
          icon={Activity}
          meta={data.scheduler.thread_alive ? "tick thread alive" : "tick thread stopped"}
        />
        <OpsProbeCard
          title="Gemini"
          status={data.gemini.status}
          detail={data.gemini.detail}
          icon={Sparkles}
          meta={data.gemini.mode ?? undefined}
        />
        <OpsProbeCard
          title="Razorpay"
          status={data.razorpay.status}
          detail={data.razorpay.detail}
          icon={Gauge}
          meta={data.razorpay.mode ?? undefined}
        />
      </div>

      <SectionHeader title="Throughput" description="Webhook inbox, action counters, and in-process HTTP latency." />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard
          label="Webhooks received"
          value={data.webhooks.received}
          format={(n) => String(Math.round(n))}
          hint={`${data.webhooks.processed} processed`}
          tone="info"
          icon={<Webhook size={16} />}
        />
        <StatCard
          label="Webhooks replayed"
          value={data.webhooks.replayed}
          format={(n) => String(Math.round(n))}
          hint={`${data.webhooks.failed} failed`}
          tone="waiting"
          icon={<RotateCw size={16} />}
        />
        <StatCard
          label="Actions executed"
          value={data.recovery_actions_executed}
          format={(n) => String(Math.round(n))}
          hint="Since process start"
          tone="ai"
          icon={<Activity size={16} />}
        />
        <StatCard
          label="Payment links"
          value={data.payment_links_sent}
          format={(n) => String(Math.round(n))}
          hint="From recovery_actions"
          tone="info"
          icon={<Link2 size={16} />}
        />
        <StatCard
          label="HTTP p95"
          value={data.http.latency_p95_ms}
          format={(n) => formatMs(n)}
          hint={`p50 ${formatMs(data.http.latency_p50_ms)} · ${data.http.request_count} req`}
          tone="waiting"
          icon={<Timer size={16} />}
        />
        <StatCard
          label="Successful retries"
          value={data.successful_retries}
          format={(n) => String(Math.round(n))}
          hint="From recovery_actions"
          tone="recovered"
          icon={<RotateCw size={16} />}
        />
      </div>
    </div>
  );
}
