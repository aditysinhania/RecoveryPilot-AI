import { ChartCard } from "@/components/shared/ChartCard";
import { formatPaise, formatPercent } from "@/lib/format";
import type { AnalyticsView } from "@/types/analytics";

interface BankDowntimeChartProps {
  bank: AnalyticsView["bank"];
}

/** Bank-timeout share of the 90-day failure mix vs queue recovery rates. */
export function BankDowntimeChart({ bank }: BankDowntimeChartProps) {
  const share = Math.round(bank.share * 100);
  return (
    <ChartCard
      title="Bank downtime impact"
      description="BANK_TIMEOUT slice from the seed-42 failure mix. Rates below are the loaded queue sample."
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-surface-raised px-3 py-2">
          <p className="text-[11px] uppercase tracking-wide text-muted">Timeout cases</p>
          <p className="mt-1 text-lg font-semibold tabular-nums text-info">{bank.cases}</p>
          <p className="text-[11px] text-muted">{formatPercent(bank.share)} of failed invoices</p>
        </div>
        <div className="rounded-lg bg-surface-raised px-3 py-2">
          <p className="text-[11px] uppercase tracking-wide text-muted">Revenue in timeouts</p>
          <p className="mt-1 text-lg font-semibold tabular-nums text-info">{formatPaise(bank.revenue_paise)}</p>
        </div>
        <div className="rounded-lg bg-surface-raised px-3 py-2">
          <p className="text-[11px] uppercase tracking-wide text-muted">Sample recovery</p>
          <p className="mt-1 text-lg font-semibold tabular-nums text-recovered">{formatPercent(bank.sample_rate, 0)}</p>
          <p className="text-[11px] text-muted">Other diagnoses {formatPercent(bank.other_rate, 0)}</p>
        </div>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-zinc-800" aria-hidden>
        <div className="h-full rounded-full bg-info" style={{ width: `${share}%` }} />
      </div>
    </ChartCard>
  );
}
