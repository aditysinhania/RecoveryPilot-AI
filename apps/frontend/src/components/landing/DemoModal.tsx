import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Play, Sparkles, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

interface DemoModalProps {
  open: boolean;
  onClose: () => void;
  primaryTo: string;
}

const CHAPTERS = [
  {
    id: "diagnosis",
    title: "AI Diagnosis",
    body: "NSF, expired card, UPI, and mandate failures classified before a retry is planned.",
  },
  {
    id: "planner",
    title: "Planner",
    body: "One bounded action: wait for payday, send a Sandbox payment link, or stop.",
  },
  {
    id: "dashboard",
    title: "Dashboard",
    body: "FitLife KPIs, AI lift, and a recovery queue operators can inspect case by case.",
  },
  {
    id: "simulator",
    title: "Simulator",
    body: "Twist seed-42 knobs locally. Engines and Razorpay stay untouched.",
  },
] as const;

/** Placeholder 2-minute demo player with chapter list and blurred backdrop. */
export function DemoModal({ open, onClose, primaryTo }: DemoModalProps) {
  const [chapter, setChapter] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }
    setChapter(0);
    setPlaying(false);
    const onKey = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open || !playing) {
      return;
    }
    const timer = window.setInterval(() => {
      setChapter((current) => (current + 1) % CHAPTERS.length);
    }, 8_000);
    return () => window.clearInterval(timer);
  }, [open, playing]);

  if (!open) {
    return null;
  }

  const active = CHAPTERS[chapter];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-canvas/70 p-4 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-labelledby="demo-title"
      onClick={onClose}
    >
      <div
        className="landing-glass relative w-full max-w-3xl overflow-hidden rounded-[24px] p-5"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="absolute right-3 top-3 z-10 rounded-lg p-1 text-muted hover:text-foreground"
          onClick={onClose}
          aria-label="Close demo video"
        >
          <X size={16} />
        </button>
        <p className="text-xs font-medium uppercase tracking-wide text-ai">2-minute product demo</p>
        <h2 id="demo-title" className="mt-1 text-lg font-semibold">
          RecoveryPilot on FitLife seed-42
        </h2>
        <div className="mt-4 overflow-hidden rounded-2xl border border-white/10 bg-canvas">
          <div className="relative aspect-video">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgb(192_132_252_/_0.25),transparent_60%)]" />
            <AnimatePresence mode="wait">
              <motion.div
                key={active.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 flex flex-col items-center justify-center px-8 text-center"
              >
                <Sparkles className="text-ai" size={28} aria-hidden />
                <p className="mt-3 text-xl font-semibold">{active.title}</p>
                <p className="mt-2 max-w-md text-sm text-muted">{active.body}</p>
              </motion.div>
            </AnimatePresence>
            <button
              type="button"
              className="absolute bottom-4 left-4 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-xs backdrop-blur"
              onClick={() => setPlaying((value) => !value)}
              aria-label={playing ? "Pause demo preview" : "Play demo preview"}
            >
              {playing ? <Loader2 size={12} className="animate-spin" aria-hidden /> : <Play size={12} aria-hidden />}
              {playing ? "Playing preview" : "Play placeholder"}
            </button>
            <p className="absolute bottom-4 right-4 text-[10px] uppercase tracking-wide text-muted">
              Placeholder player
            </p>
          </div>
        </div>
        <ul className="mt-4 grid gap-2 sm:grid-cols-4">
          {CHAPTERS.map((item, index) => (
            <li key={item.id}>
              <button
                type="button"
                className={`w-full rounded-xl border px-3 py-2 text-left text-xs ${
                  index === chapter ? "border-ai bg-ai-muted" : "border-white/10 text-muted"
                }`}
                onClick={() => {
                  setChapter(index);
                  setPlaying(false);
                }}
              >
                <span className="font-medium text-foreground">0{index + 1} {item.title}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-5 flex flex-wrap gap-2">
          <Link to="/demo" className="landing-cta rounded-2xl px-4 py-2 text-sm font-semibold text-canvas" onClick={onClose}>
            Try Live Demo
          </Link>
          <Link to={primaryTo} className="rounded-2xl border border-white/15 px-4 py-2 text-sm" onClick={onClose}>
            Start free trial
          </Link>
        </div>
      </div>
    </div>
  );
}
