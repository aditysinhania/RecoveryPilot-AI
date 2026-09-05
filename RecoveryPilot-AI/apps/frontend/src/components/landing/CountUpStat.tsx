import { useInView } from "framer-motion";
import { useRef } from "react";
import { useCountUp } from "@/hooks/useCountUp";

interface CountUpStatProps {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  className?: string;
}

/** Count-up that starts when the KPI card enters the viewport. */
export function CountUpStat({
  value,
  prefix = "",
  suffix = "",
  decimals = 0,
  className = "",
}: CountUpStatProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const visible = useInView(ref, { once: true, amount: 0.25 });
  const animated = useCountUp(visible ? value : 0, 900);
  const shown = decimals > 0 ? animated.toFixed(decimals) : String(Math.round(animated));

  return (
    <span ref={ref} className={className}>
      {prefix}
      {shown}
      {suffix}
    </span>
  );
}
