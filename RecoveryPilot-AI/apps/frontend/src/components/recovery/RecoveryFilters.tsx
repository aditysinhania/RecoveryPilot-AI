import { useEffect, useState, type ChangeEvent, type ReactNode } from "react";
import { ChevronDown, Search, SlidersHorizontal } from "lucide-react";
import {
  CUSTOMER_SEGMENTS,
  DIAGNOSIS_VALUES,
  PAYMENT_METHODS,
  PLANNER_STRATEGIES,
  POLICY_DECISIONS,
  PRIORITY_BANDS,
  RECOVERY_STATUSES,
  type RecoveryQueueFilters,
} from "@/types/recovery";
import { advancedFilterCount, EMPTY_FILTERS, hasActiveFilters } from "@/lib/recoveryMap";
import { titleCase } from "@/lib/format";
import type { MerchantOption } from "@/types/dashboard";

interface RecoveryFiltersProps {
  filters: RecoveryQueueFilters;
  merchants: MerchantOption[];
  onChange: (next: RecoveryQueueFilters) => void;
}

function Field({
  id,
  label,
  children,
  className = "",
  visibleLabel = false,
}: {
  id: string;
  label: string;
  children: ReactNode;
  className?: string;
  visibleLabel?: boolean;
}) {
  return (
    <label className={`block min-w-0 ${className}`} htmlFor={id}>
      {visibleLabel ? (
        <span className="mb-0.5 block text-[10px] font-medium uppercase tracking-wide text-muted">{label}</span>
      ) : (
        <span className="sr-only">{label}</span>
      )}
      {children}
    </label>
  );
}

const CONTROL =
  "h-8 w-full rounded-md border border-border bg-canvas px-2.5 text-xs text-foreground placeholder:text-zinc-500";

/** Compact 2-row filter toolbar. Advanced filters stay collapsed until needed. */
export function RecoveryFilters({ filters, merchants, onChange }: RecoveryFiltersProps) {
  const advancedCount = advancedFilterCount(filters);
  const [advancedOpen, setAdvancedOpen] = useState(advancedCount > 0);

  useEffect(() => {
    if (advancedCount > 0) {
      setAdvancedOpen(true);
    }
  }, [advancedCount]);

  const patch = (key: keyof RecoveryQueueFilters, value: string): void => {
    onChange({ ...filters, [key]: value });
  };

  const onSelect = (key: keyof RecoveryQueueFilters) => (event: ChangeEvent<HTMLSelectElement | HTMLInputElement>) => {
    patch(key, event.target.value);
  };

  return (
    <section className="min-w-0 rounded-xl border border-border bg-surface px-3 py-2" aria-label="Recovery filters">
      <div className="flex min-w-0 flex-wrap items-center gap-2 lg:flex-nowrap">
        <label className="relative min-w-[180px] flex-1" htmlFor="queue-search">
          <span className="sr-only">Search</span>
          <Search size={13} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" />
          <input
            id="queue-search"
            type="search"
            value={filters.search}
            onChange={onSelect("search")}
            placeholder="Search customer or payment id"
            className={`${CONTROL} pl-8`}
          />
        </label>
        <Field id="filter-status" label="Recovery status" className="w-[148px]">
          <select id="filter-status" className={CONTROL} value={filters.status} onChange={onSelect("status")}>
            <option value="">All statuses</option>
            {RECOVERY_STATUSES.map((value) => (
              <option key={value} value={value}>
                {titleCase(value)}
              </option>
            ))}
          </select>
        </Field>
        <Field id="filter-priority" label="Priority" className="w-[120px]">
          <select id="filter-priority" className={CONTROL} value={filters.priority} onChange={onSelect("priority")}>
            <option value="">All priority</option>
            {PRIORITY_BANDS.map((value) => (
              <option key={value} value={value}>
                {titleCase(value)}
              </option>
            ))}
          </select>
        </Field>
        <Field id="filter-diagnosis" label="Diagnosis" className="w-[160px]">
          <select id="filter-diagnosis" className={CONTROL} value={filters.diagnosis} onChange={onSelect("diagnosis")}>
            <option value="">All diagnoses</option>
            {DIAGNOSIS_VALUES.map((value) => (
              <option key={value} value={value}>
                {titleCase(value)}
              </option>
            ))}
          </select>
        </Field>
        <button
          type="button"
          className={`inline-flex h-8 items-center gap-1.5 rounded-md border px-2.5 text-xs ${
            advancedOpen || advancedCount > 0
              ? "border-info/40 bg-info-muted text-info"
              : "border-border text-muted hover:bg-surface-hover hover:text-foreground"
          }`}
          aria-expanded={advancedOpen}
          onClick={() => setAdvancedOpen((value) => !value)}
        >
          <SlidersHorizontal size={13} aria-hidden />
          Advanced
          {advancedCount > 0 ? (
            <span className="rounded-full bg-info px-1.5 text-[10px] font-semibold text-canvas">{advancedCount}</span>
          ) : (
            <ChevronDown size={12} className={advancedOpen ? "rotate-180" : ""} aria-hidden />
          )}
        </button>
        <button
          type="button"
          className="ml-auto h-8 rounded-md border border-border px-2.5 text-xs text-muted hover:bg-surface-hover hover:text-foreground disabled:opacity-40"
          disabled={!hasActiveFilters(filters)}
          onClick={() => onChange({ ...EMPTY_FILTERS, merchantId: filters.merchantId })}
        >
          Clear
        </button>
      </div>
      {advancedOpen ? (
        <div className="mt-2 border-t border-border pt-2">
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-muted">Advanced Filters</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          <Field id="filter-merchant" label="Merchant" visibleLabel>
            <select id="filter-merchant" className={CONTROL} value={filters.merchantId} onChange={onSelect("merchantId")}>
              {merchants.map((merchant) => (
                <option key={merchant.id} value={merchant.id}>
                  {merchant.merchant_name}
                </option>
              ))}
            </select>
          </Field>
          <Field id="filter-policy" label="Policy decision" visibleLabel>
            <select id="filter-policy" className={CONTROL} value={filters.policy} onChange={onSelect("policy")}>
              <option value="">All policy</option>
              {POLICY_DECISIONS.map((value) => (
                <option key={value} value={value}>
                  {titleCase(value)}
                </option>
              ))}
            </select>
          </Field>
          <Field id="filter-strategy" label="Planner strategy" visibleLabel>
            <select id="filter-strategy" className={CONTROL} value={filters.strategy} onChange={onSelect("strategy")}>
              <option value="">All strategies</option>
              {PLANNER_STRATEGIES.map((value) => (
                <option key={value} value={value}>
                  {titleCase(value)}
                </option>
              ))}
            </select>
          </Field>
          <Field id="filter-method" label="Payment method" visibleLabel>
            <select
              id="filter-method"
              className={CONTROL}
              value={filters.paymentMethod}
              onChange={onSelect("paymentMethod")}
            >
              <option value="">All methods</option>
              {PAYMENT_METHODS.map((value) => (
                <option key={value} value={value}>
                  {titleCase(value)}
                </option>
              ))}
            </select>
          </Field>
          <Field id="filter-segment" label="Customer segment" visibleLabel>
            <select id="filter-segment" className={CONTROL} value={filters.segment} onChange={onSelect("segment")}>
              <option value="">All segments</option>
              {CUSTOMER_SEGMENTS.map((value) => (
                <option key={value} value={value}>
                  {titleCase(value)}
                </option>
              ))}
            </select>
          </Field>
          <Field id="filter-min" label="Min amount (₹)" visibleLabel>
            <input
              id="filter-min"
              type="number"
              min={0}
              inputMode="decimal"
              placeholder="Min ₹"
              className={CONTROL}
              value={filters.amountMin}
              onChange={onSelect("amountMin")}
            />
          </Field>
          <Field id="filter-max" label="Max amount (₹)" visibleLabel>
            <input
              id="filter-max"
              type="number"
              min={0}
              inputMode="decimal"
              placeholder="Max ₹"
              className={CONTROL}
              value={filters.amountMax}
              onChange={onSelect("amountMax")}
            />
          </Field>
          <Field id="filter-from" label="Failed from" visibleLabel>
            <input
              id="filter-from"
              type="date"
              className={CONTROL}
              value={filters.dateFrom}
              onChange={onSelect("dateFrom")}
            />
          </Field>
          <Field id="filter-to" label="Failed to" visibleLabel>
            <input
              id="filter-to"
              type="date"
              className={CONTROL}
              value={filters.dateTo}
              onChange={onSelect("dateTo")}
            />
          </Field>
          </div>
        </div>
      ) : null}
    </section>
  );
}
