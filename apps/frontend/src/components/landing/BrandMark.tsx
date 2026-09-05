import { useId } from "react";

/** Compact RecoveryPilot mark. Gradient stays on brand tokens. */
export function BrandMark({ className = "h-8 w-8" }: { className?: string }) {
  const fillId = useId().replace(/:/g, "");

  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect width="32" height="32" rx="9" fill={`url(#${fillId})`} />
      <path
        d="M9 22V10h7.2c2.7 0 4.4 1.5 4.4 3.7 0 1.5-.8 2.6-2.1 3.1L21.8 22h-3.1l-3.1-5.1H12V22H9Zm3-7.4h4c1.2 0 1.9-.6 1.9-1.5S17.2 12 16 12H12v2.6Z"
        fill="#09090b"
      />
      <defs>
        <linearGradient id={fillId} x1="4" y1="2" x2="30" y2="30">
          <stop stopColor="#c084fc" />
          <stop offset="1" stopColor="#38bdf8" />
        </linearGradient>
      </defs>
    </svg>
  );
}
