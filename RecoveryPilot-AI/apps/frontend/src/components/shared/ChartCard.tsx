import { motion } from "framer-motion";
import type { ReactNode } from "react";
import { SectionHeader } from "@/components/shared/SectionHeader";
import { cardHover, chartFade } from "@/lib/motion";

interface ChartCardProps {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

/** Card wrapper for Recharts with a short fade-in. */
export function ChartCard({
  title,
  description,
  action,
  children,
  className = "",
}: ChartCardProps) {
  return (
    <motion.section
      {...chartFade}
      {...cardHover}
      className={`rounded-xl border border-border bg-surface p-4 shadow-[var(--shadow-card)] ${className}`}
    >
      <SectionHeader title={title} description={description} action={action} />
      {children}
    </motion.section>
  );
}
