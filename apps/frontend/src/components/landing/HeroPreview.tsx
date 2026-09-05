import { motion, useScroll, useTransform } from "framer-motion";

const FLOATS = [
  { label: "Recovery rate", value: "69.3%", className: "top-2 right-0 sm:-right-8" },
  { label: "Revenue recovered", value: "₹5.83L", className: "bottom-20 -left-2 sm:-left-10" },
  { label: "Lift vs retry", value: "+35.2%", className: "top-1/3 -left-1 sm:-left-12" },
  { label: "Retries prevented", value: "117", className: "bottom-4 right-4 sm:-right-6" },
] as const;

/** Floating FitLife dashboard chrome for the hero. */
export function HeroPreview() {
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 480], [0, 36]);

  return (
    <motion.div style={{ y }} className="relative mx-auto w-full max-w-lg lg:max-w-none">
      <motion.div
        className="absolute -inset-8 rounded-[2rem] bg-gradient-to-br from-ai/30 via-transparent to-info/25 blur-3xl"
        animate={{ opacity: [0.45, 0.75, 0.45] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
        aria-hidden
      />
      <motion.div
        className="landing-glass landing-gradient-border relative rounded-[24px] p-3"
        animate={{ y: [0, -10, 0] }}
        transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}
      >
        <div className="overflow-hidden rounded-[18px] border border-border bg-canvas">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-blocked" />
              <span className="h-2 w-2 rounded-full bg-waiting" />
              <span className="h-2 w-2 rounded-full bg-recovered" />
            </div>
            <p className="text-[10px] uppercase tracking-wide text-muted">FitLife Gym · Sandbox</p>
            <p className="text-[10px] text-ai">Live shape</p>
          </div>
          <div className="grid grid-cols-[64px_1fr] sm:grid-cols-[88px_1fr]">
            <aside className="space-y-2 border-r border-border bg-canvas-muted p-2">
              {["Home", "Queue", "Lab"].map((item, index) => (
                <div
                  key={item}
                  className={`rounded-lg px-1.5 py-1.5 text-[9px] ${index === 0 ? "bg-ai-muted text-ai" : "text-muted"}`}
                >
                  {item}
                </div>
              ))}
            </aside>
            <div className="space-y-2 p-3">
              <div className="grid grid-cols-2 gap-2">
                <MiniKpi label="Recovered" value="₹5.83L" tone="text-recovered" />
                <MiniKpi label="At risk" value="₹8.42L" tone="text-waiting" />
              </div>
              <svg viewBox="0 0 240 72" className="h-20 w-full" aria-hidden>
                <defs>
                  <linearGradient id="hero-line" x1="0" y1="0" x2="1" y2="0">
                    <stop stopColor="#c084fc" />
                    <stop offset="1" stopColor="#38bdf8" />
                  </linearGradient>
                </defs>
                <path
                  d="M4 58 C 28 54, 40 40, 58 42 S 90 20, 112 24 S 150 48, 172 28 S 210 12, 236 18"
                  fill="none"
                  stroke="url(#hero-line)"
                  strokeWidth="2.4"
                />
                <path
                  d="M4 62 C 28 60, 40 52, 58 54 S 90 44, 112 46 S 150 58, 172 50 S 210 42, 236 44"
                  fill="none"
                  stroke="#52525b"
                  strokeWidth="1.4"
                  strokeDasharray="3 4"
                />
              </svg>
              <div className="rounded-xl border border-ai/30 bg-surface p-2">
                <p className="text-[10px] font-medium text-ai">AI suggestions</p>
                <p className="mt-1 text-[11px] text-muted">Keep NSF on payday wait. 117 harmful retries already stopped.</p>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
      {FLOATS.map((card) => (
        <motion.div
          key={card.label}
          className={`landing-glass absolute hidden rounded-2xl px-3 py-2 sm:block ${card.className}`}
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 5 + card.label.length / 8, repeat: Infinity, ease: "easeInOut" }}
        >
          <p className="text-[10px] uppercase tracking-wide text-muted">{card.label}</p>
          <p className="text-sm font-semibold text-foreground">{card.value}</p>
        </motion.div>
      ))}
      <div className="mt-4 grid grid-cols-2 gap-2 sm:hidden">
        {FLOATS.map((card) => (
          <div key={card.label} className="landing-glass rounded-2xl px-3 py-2">
            <p className="text-[10px] text-muted">{card.label}</p>
            <p className="text-sm font-semibold">{card.value}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function MiniKpi({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-2">
      <p className="text-[10px] text-muted">{label}</p>
      <p className={`text-sm font-semibold ${tone}`}>{value}</p>
    </div>
  );
}
