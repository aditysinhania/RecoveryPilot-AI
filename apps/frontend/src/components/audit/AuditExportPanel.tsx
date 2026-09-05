import { Download } from "lucide-react";
import type { AuditEventView } from "@/types/audit";

const CSV_COLUMNS = [
  "timestamp",
  "event_type",
  "actor",
  "summary",
  "request_id",
  "correlation_id",
  "recovery_case_id",
  "policy_decision",
  "severity",
] as const;

function csvEscape(value: string): string {
  if (/[",\n]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function toCsv(events: AuditEventView[]): string {
  const lines = [CSV_COLUMNS.join(",")];
  for (const event of events) {
    const row = [
      event.timestamp,
      event.display_type,
      event.actor,
      event.summary,
      event.request_id,
      event.correlation_id,
      event.recovery_case_id ?? "",
      event.policy_decision ?? "",
      event.severity,
    ];
    lines.push(row.map((cell) => csvEscape(String(cell))).join(","));
  }
  return lines.join("\n");
}

function download(filename: string, mime: string, body: string): void {
  const blob = new Blob([body], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

/** Download visible events as JSON. */
export function exportAuditJson(events: AuditEventView[]): void {
  const stamp = new Date().toISOString().slice(0, 10);
  download(`audit-timeline-${stamp}.json`, "application/json", JSON.stringify(events, null, 2));
}

/** Download visible events as CSV. */
export function exportAuditCsv(events: AuditEventView[]): void {
  const stamp = new Date().toISOString().slice(0, 10);
  download(`audit-timeline-${stamp}.csv`, "text/csv;charset=utf-8", toCsv(events));
}

interface AuditExportButtonsProps {
  events: AuditEventView[];
}

/** Toolbar JSON/CSV actions. No server call. */
export function AuditExportButtons({ events }: AuditExportButtonsProps) {
  return (
    <div className="flex items-center gap-1.5">
      <button
        type="button"
        className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs text-foreground hover:bg-surface-hover disabled:opacity-40"
        disabled={events.length === 0}
        onClick={() => exportAuditJson(events)}
      >
        <Download size={13} aria-hidden />
        JSON
      </button>
      <button
        type="button"
        className="inline-flex h-8 items-center gap-1 rounded-md border border-border px-2.5 text-xs text-foreground hover:bg-surface-hover disabled:opacity-40"
        disabled={events.length === 0}
        onClick={() => exportAuditCsv(events)}
      >
        <Download size={13} aria-hidden />
        CSV
      </button>
    </div>
  );
}
