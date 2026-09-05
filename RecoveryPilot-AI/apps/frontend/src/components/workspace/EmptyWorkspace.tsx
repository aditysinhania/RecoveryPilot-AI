import { BookOpen, Database, FlaskConical, Wallet } from "lucide-react";
import { Link } from "react-router-dom";
import { useDemoMode } from "@/demo/DemoContext";

interface EmptyWorkspaceProps {
  onImportDemo: () => void;
}

/** Illustrated empty merchant workspace. Never render blank charts here. */
export function EmptyWorkspace({ onImportDemo }: EmptyWorkspaceProps) {
  const { opsPath } = useDemoMode();
  return (
    <div className="mx-auto max-w-3xl py-6" role="status">
      <div className="relative overflow-hidden rounded-2xl border border-border bg-surface px-6 py-10 text-center shadow-[var(--shadow-card)]">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgb(192_132_252_/_0.18),transparent_55%)]"
          aria-hidden
        />
        <svg
          viewBox="0 0 280 120"
          className="relative mx-auto h-28 w-full max-w-sm text-ai"
          aria-hidden
        >
          <rect x="24" y="28" width="232" height="72" rx="16" className="fill-canvas-muted stroke-border" strokeWidth="1.5" />
          <rect x="40" y="44" width="56" height="40" rx="8" className="fill-ai-muted" />
          <rect x="108" y="44" width="56" height="40" rx="8" className="fill-info-muted" />
          <rect x="176" y="44" width="56" height="40" rx="8" className="fill-recovered-muted" />
          <circle cx="68" cy="64" r="8" className="fill-ai/50" />
          <path d="M120 72h32M188 56v24" className="stroke-muted" strokeWidth="3" strokeLinecap="round" />
        </svg>
        <h1 className="relative mt-4 text-lg font-semibold tracking-tight">Your workspace is ready</h1>
        <p className="relative mx-auto mt-2 max-w-md text-sm text-muted">
          No failed payments yet. Connect Razorpay Sandbox, import the FitLife seed-42 dataset, or open the simulator
          lab — charts stay hidden until there is something to plot.
        </p>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <Link
          to={opsPath("/settings")}
          className="rp-hover-lift rp-glow-border rounded-xl border border-border bg-surface p-4 text-left"
        >
          <Wallet size={18} className="text-info" aria-hidden />
          <p className="mt-2 text-sm font-semibold">Connect Razorpay Sandbox</p>
          <p className="mt-1 text-xs text-muted">Store test keys. Live capture is never called from this UI.</p>
        </Link>
        <button
          type="button"
          onClick={onImportDemo}
          className="rp-hover-lift rp-glow-border rounded-xl border border-border bg-surface p-4 text-left"
        >
          <Database size={18} className="text-ai" aria-hidden />
          <p className="mt-2 text-sm font-semibold">Import Demo Dataset</p>
          <p className="mt-1 text-xs text-muted">Switch to FitLife seed-42 and explore the full queue.</p>
        </button>
        <a
          href="/#docs"
          className="rp-hover-lift rp-glow-border rounded-xl border border-border bg-surface p-4 text-left"
        >
          <BookOpen size={18} className="text-recovered" aria-hidden />
          <p className="mt-2 text-sm font-semibold">Read Documentation</p>
          <p className="mt-1 text-xs text-muted">Architecture, auth, and how the demo workspace is assembled.</p>
        </a>
        <Link
          to={opsPath("/simulator")}
          className="rp-hover-lift rp-glow-border rounded-xl border border-border bg-surface p-4 text-left"
        >
          <FlaskConical size={18} className="text-waiting" aria-hidden />
          <p className="mt-2 text-sm font-semibold">Open Simulator</p>
          <p className="mt-1 text-xs text-muted">Replay seed-42 locally. Engines and Razorpay stay untouched.</p>
        </Link>
      </div>
    </div>
  );
}
