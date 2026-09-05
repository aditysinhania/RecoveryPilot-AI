import { useEffect, useState } from "react";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { formatCountdown, formatDateTime, titleCase } from "@/lib/format";
import type { CaseDrawerModel } from "@/types/recovery";

interface PolicyCardProps {
  policy: CaseDrawerModel["policy"];
}

function ChannelList({ label, values, tone }: { label: string; values: string[]; tone: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-muted">{label}</p>
      <div className="mt-1.5 flex flex-wrap gap-1">
        {values.length === 0 ? (
          <span className="text-xs text-muted">None</span>
        ) : (
          values.map((channel) => (
            <span key={channel} className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${tone}`}>
              {titleCase(channel)}
            </span>
          ))
        )}
      </div>
    </div>
  );
}

function CooldownTimer({ until }: { until: string }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);
  const remaining = formatCountdown(until, now);
  const ended = remaining === "Cooldown ended";
  return (
    <p className={`mt-3 text-xs ${ended ? "text-muted" : "text-waiting"}`}>
      {ended ? remaining : `Cooldown · ${remaining}`}
      <span className="ml-1 text-zinc-500">({formatDateTime(until)})</span>
    </p>
  );
}

/** Policy fold: decision, channels, cooldown timer, evaluated rules. */
export function PolicyCard({ policy }: PolicyCardProps) {
  return (
    <section className="rounded-xl border border-border bg-surface-raised p-4" aria-labelledby="policy-heading">
      <div className="flex items-center justify-between gap-2">
        <h3 id="policy-heading" className="text-[11px] font-semibold uppercase tracking-wide text-muted">
          Policy
        </h3>
        <StatusBadge status={policy.decision} />
      </div>
      <p className="mt-2 text-xs text-muted">
        Decision priority <span className="tabular-nums text-foreground">{policy.decision_priority}</span>
      </p>
      {policy.reasons.length > 0 ? (
        <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-foreground">
          {policy.reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-xs text-muted">No blocking reasons. Recovery is allowed.</p>
      )}
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <ChannelList label="Allowed channels" values={policy.allowed_channels} tone="bg-recovered-muted text-recovered" />
        <ChannelList label="Blocked channels" values={policy.blocked_channels} tone="bg-blocked-muted text-blocked" />
      </div>
      {policy.cooldown_until ? <CooldownTimer until={policy.cooldown_until} /> : null}
      {policy.evaluated_rules.length > 0 ? (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full table-fixed text-left text-[11px]">
            <thead className="text-muted">
              <tr>
                <th className="w-[34%] py-1 font-medium">Rule</th>
                <th className="w-[22%] py-1 font-medium">Result</th>
                <th className="w-[44%] py-1 font-medium">Reason</th>
              </tr>
            </thead>
            <tbody>
              {policy.evaluated_rules.map((row) => (
                <tr key={`${row.policy_name}-${row.result}`} className="border-t border-border">
                  <td className="truncate py-1.5 pr-1" title={titleCase(row.policy_name)}>
                    {titleCase(row.policy_name)}
                  </td>
                  <td className="py-1.5 pr-1">
                    <StatusBadge status={row.result} />
                  </td>
                  <td className="truncate py-1.5 text-muted" title={row.reason}>
                    {row.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
