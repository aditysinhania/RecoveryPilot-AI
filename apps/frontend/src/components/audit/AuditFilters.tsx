import type { ChangeEvent, ReactNode } from "react";
import { Search } from "lucide-react";
import { titleCase } from "@/lib/format";
import { activeAuditFilterCount, EMPTY_AUDIT_FILTERS } from "@/lib/auditMap";
import {
  AUDIT_ACTORS,
  AUDIT_EVENT_TYPES,
  AUDIT_SEVERITIES,
  type AuditFilters,
} from "@/types/audit";

interface AuditFiltersProps {
  filters: AuditFilters;
  onChange: (next: AuditFilters) => void;
  actions?: ReactNode;
}

const CONTROL =
  "h-8 w-full rounded-md border border-border bg-canvas px-2.5 text-xs text-foreground placeholder:text-zinc-500";

function Field({
  id,
  label,
  children,
  className = "",
}: {
  id: string;
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <label className={`block min-w-0 ${className}`} htmlFor={id}>
      <span className="mb-0.5 block text-[10px] font-medium uppercase tracking-wide text-muted">{label}</span>
      {children}
    </label>
  );
}

/** Sticky explorer filters. Correlation and case ids hit GET /audit/events. */
export function AuditFilters({ filters, onChange, actions }: AuditFiltersProps) {
  const active = activeAuditFilterCount(filters);

  const patch = (key: keyof AuditFilters, value: string): void => {
    onChange({ ...filters, [key]: value });
  };

  const onField = (key: keyof AuditFilters) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    patch(key, event.target.value);
  };

  return (
    <section
      className="sticky top-0 z-20 rounded-xl border border-border bg-surface/95 px-3 py-2 shadow-[var(--shadow-card)] backdrop-blur"
      aria-label="Audit filters"
    >
      <div className="grid grid-cols-2 gap-2 lg:grid-cols-4 xl:grid-cols-7">
        <Field id="audit-correlation" label="Correlation ID" className="col-span-2">
          <span className="relative block">
            <Search size={13} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              id="audit-correlation"
              type="search"
              value={filters.correlationId}
              onChange={onField("correlationId")}
              placeholder="corr-… or case uuid"
              className={`${CONTROL} pl-8`}
              autoComplete="off"
            />
          </span>
        </Field>
        <Field id="audit-case" label="Recovery case ID" className="col-span-2">
          <input
            id="audit-case"
            type="search"
            value={filters.caseId}
            onChange={onField("caseId")}
            placeholder="UUID"
            className={CONTROL}
            autoComplete="off"
          />
        </Field>
        <Field id="audit-actor" label="Actor">
          <select id="audit-actor" className={CONTROL} value={filters.actor} onChange={onField("actor")}>
            <option value="">All actors</option>
            {AUDIT_ACTORS.map((value) => (
              <option key={value} value={value}>
                {titleCase(value)}
              </option>
            ))}
          </select>
        </Field>
        <Field id="audit-type" label="Event type">
          <select id="audit-type" className={CONTROL} value={filters.eventType} onChange={onField("eventType")}>
            <option value="">All types</option>
            {AUDIT_EVENT_TYPES.map((value) => (
              <option key={value} value={value}>
                {titleCase(value)}
              </option>
            ))}
          </select>
        </Field>
        <Field id="audit-severity" label="Severity">
          <select id="audit-severity" className={CONTROL} value={filters.severity} onChange={onField("severity")}>
            <option value="">All severity</option>
            {AUDIT_SEVERITIES.map((value) => (
              <option key={value} value={value}>
                {titleCase(value)}
              </option>
            ))}
          </select>
        </Field>
        <Field id="audit-from" label="From">
          <input id="audit-from" type="date" className={CONTROL} value={filters.dateFrom} onChange={onField("dateFrom")} />
        </Field>
        <Field id="audit-to" label="To">
          <input id="audit-to" type="date" className={CONTROL} value={filters.dateTo} onChange={onField("dateTo")} />
        </Field>
      </div>
      <div className="mt-2 flex flex-wrap items-center justify-end gap-1.5">
        {actions}
        <button
          type="button"
          className="h-8 rounded-md border border-border px-2.5 text-xs text-muted hover:bg-surface-hover hover:text-foreground disabled:opacity-40"
          disabled={active === 0}
          onClick={() => onChange({ ...EMPTY_AUDIT_FILTERS })}
        >
          Clear
        </button>
      </div>
    </section>
  );
}
