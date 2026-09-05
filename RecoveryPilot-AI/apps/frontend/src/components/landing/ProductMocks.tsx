import { AUDIT_EVENTS, QUEUE_ROWS, SIM_KNOBS } from "@/components/landing/data";

export type ProductMockKind = "dashboard" | "queue" | "analytics" | "audit" | "simulator";

interface ProductMockProps {
  kind: ProductMockKind;
}

/** CSS recreations of RecoveryPilot ops screens (no stock illustrations). */
export function ProductMock({ kind }: ProductMockProps) {
  return (
    <div className="landing-glass overflow-hidden rounded-[24px]">
      <div className="flex items-center gap-1.5 border-b border-white/5 px-3 py-2">
        <span className="h-2 w-2 rounded-full bg-blocked" />
        <span className="h-2 w-2 rounded-full bg-waiting" />
        <span className="h-2 w-2 rounded-full bg-recovered" />
        <span className="ml-2 text-[10px] uppercase tracking-wide text-muted">{titleFor(kind)}</span>
      </div>
      <div className="bg-canvas p-3">
        {kind === "dashboard" ? <DashboardMock /> : null}
        {kind === "queue" ? <QueueMock /> : null}
        {kind === "analytics" ? <AnalyticsMock /> : null}
        {kind === "audit" ? <AuditMock /> : null}
        {kind === "simulator" ? <SimulatorMock /> : null}
      </div>
    </div>
  );
}

function titleFor(kind: ProductMockKind): string {
  switch (kind) {
    case "dashboard":
      return "Dashboard";
    case "queue":
      return "Recovery queue";
    case "analytics":
      return "Analytics";
    case "audit":
      return "Audit timeline";
    case "simulator":
      return "Simulator lab";
  }
}

function DashboardMock() {
  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2">
        {[
          ["Rate", "69.3%", "text-recovered"],
          ["Recovered", "₹5.83L", "text-ai"],
          ["Waiting", "48", "text-waiting"],
        ].map(([label, value, tone]) => (
          <div key={label} className="rounded-xl border border-border bg-surface p-2">
            <p className="text-[9px] uppercase text-muted">{label}</p>
            <p className={`text-sm font-semibold ${tone}`}>{value}</p>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-1">
        {[70, 45, 88, 52, 91, 63].map((h, i) => (
          <div key={i} className="flex h-16 items-end rounded-lg bg-surface px-1">
            <div className="w-full rounded-t bg-gradient-to-t from-ai to-info" style={{ height: `${h}%` }} />
          </div>
        ))}
      </div>
    </div>
  );
}

function QueueMock() {
  return (
    <div className="overflow-hidden rounded-xl border border-border">
      {QUEUE_ROWS.map((row) => (
        <div key={row.name} className="grid grid-cols-[1fr_auto_auto] items-center gap-2 border-b border-border px-2 py-2 last:border-0">
          <div>
            <p className="text-xs font-medium">{row.name}</p>
            <p className="text-[10px] text-muted">
              {row.plan} · {row.diagnosis}
            </p>
          </div>
          <p className="text-xs tabular-nums text-muted">{row.amount}</p>
          <span className="rounded-full bg-ai-muted px-2 py-0.5 text-[10px] text-ai">{row.status}</span>
        </div>
      ))}
    </div>
  );
}

function AnalyticsMock() {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="flex items-center justify-center">
        <div className="relative h-28 w-28 rounded-full border-[10px] border-ai border-r-info border-b-waiting border-l-recovered" />
      </div>
      <div className="space-y-2">
        {[
          ["NSF / payday", "43%"],
          ["UPI congestion", "18%"],
          ["Mandate revoked", "11%"],
        ].map(([label, value]) => (
          <div key={label}>
            <div className="flex justify-between text-[10px] text-muted">
              <span>{label}</span>
              <span>{value}</span>
            </div>
            <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-hover">
              <div className="h-full rounded-full bg-gradient-to-r from-ai to-info" style={{ width: value }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AuditMock() {
  return (
    <ol className="space-y-2">
      {AUDIT_EVENTS.map((item, index) => (
        <li key={item.summary} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span
              className={`mt-1 h-2 w-2 rounded-full ${
                item.tone === "recovered"
                  ? "bg-recovered"
                  : item.tone === "ai"
                    ? "bg-ai"
                    : item.tone === "info"
                      ? "bg-info"
                      : "bg-waiting"
              }`}
            />
            {index < AUDIT_EVENTS.length - 1 ? <span className="mt-1 w-px flex-1 bg-border" /> : null}
          </div>
          <div className="rounded-xl border border-border bg-surface px-3 py-2">
            <p className="text-[10px] uppercase text-muted">{item.actor}</p>
            <p className="text-xs">{item.summary}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

function SimulatorMock() {
  return (
    <div className="grid gap-3 sm:grid-cols-[140px_1fr]">
      <div className="space-y-1.5 rounded-xl border border-border bg-surface p-2">
        {SIM_KNOBS.map((knob, index) => (
          <label key={knob} className="flex items-center gap-2 text-[10px] text-muted">
            <span className={`h-3 w-6 rounded-full ${index !== 2 ? "bg-ai" : "bg-surface-hover"}`}>
              <span className={`mt-0.5 block h-2 w-2 rounded-full bg-canvas ${index !== 2 ? "ml-3" : "ml-0.5"}`} />
            </span>
            {knob}
          </label>
        ))}
      </div>
      <div className="space-y-2">
        <div className="rounded-xl border border-border bg-surface p-2">
          <p className="text-[10px] text-muted">AI vs baseline</p>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-hover">
            <div className="h-full w-[69%] rounded-full bg-gradient-to-r from-ai to-info" />
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-surface-hover">
            <div className="h-full w-[34%] rounded-full bg-zinc-600" />
          </div>
          <p className="mt-2 text-xs text-recovered">+35.2 pts lift · ₹2.97L extra</p>
        </div>
      </div>
    </div>
  );
}
