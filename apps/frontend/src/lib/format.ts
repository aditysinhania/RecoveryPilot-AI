const INR = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const INR_EXACT = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const COMPACT = new Intl.NumberFormat("en-IN", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const RELATIVE = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

/** Format integer paise as rupees with Indian grouping, e.g. ₹5,83,495. */
export function formatPaise(paise: number, exact = false): string {
  const rupees = paise / 100;
  if (exact && Math.abs(rupees) < 1000) {
    return INR_EXACT.format(rupees);
  }
  return INR.format(Math.round(rupees));
}

/** Format a 0–1 ratio as a percentage with one decimal place. */
export function formatPercent(ratio: number, digits = 1): string {
  return `${(ratio * 100).toFixed(digits)}%`;
}

/** Compact count or rupee magnitude for dense KPI subtitles. */
export function formatCompact(value: number): string {
  return COMPACT.format(value);
}

/** Compact rupees from paise (₹5.8L). */
export function formatCompactPaise(paise: number): string {
  return `₹${COMPACT.format(paise / 100)}`;
}

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** Relative time from an ISO timestamp, falling back to a short date. */
export function formatRelativeTime(iso: string, now = Date.now()): string {
  const then = Date.parse(iso);
  if (Number.isNaN(then)) {
    return "Unknown";
  }
  const delta = then - now;
  const abs = Math.abs(delta);
  if (abs < MINUTE) {
    return "just now";
  }
  if (abs < HOUR) {
    return RELATIVE.format(Math.round(delta / MINUTE), "minute");
  }
  if (abs < DAY) {
    return RELATIVE.format(Math.round(delta / HOUR), "hour");
  }
  if (abs < 30 * DAY) {
    return RELATIVE.format(Math.round(delta / DAY), "day");
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(then);
}

/** Short chart axis date (05 Sep). */
export function formatChartDate(isoDate: string): string {
  const parsed = Date.parse(isoDate);
  if (Number.isNaN(parsed)) {
    return isoDate;
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
  }).format(parsed);
}

/** Remaining time until an ISO timestamp, for policy cooldown. */
export function formatCountdown(iso: string, now = Date.now()): string {
  const then = Date.parse(iso);
  if (Number.isNaN(then)) {
    return "Unknown";
  }
  const delta = then - now;
  if (delta <= 0) {
    return "Cooldown ended";
  }
  const hours = Math.floor(delta / HOUR);
  const minutes = Math.floor((delta % HOUR) / MINUTE);
  const seconds = Math.floor((delta % MINUTE) / 1000);
  if (hours >= 48) {
    return `${Math.floor(hours / 24)}d ${hours % 24}h remaining`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m remaining`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s remaining`;
  }
  return `${seconds}s remaining`;
}

/** Absolute IST datetime for drawer timestamps. */
export function formatDateTime(iso: string): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return "Unknown";
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  }).format(parsed);
}

/** Calendar date (YYYY-MM-DD) in IST. */
export function isoDate(iso: string): string {
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return "";
  }
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(parsed);
}

/** Human diagnosis / status labels for table cells. */
export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

/** Two-letter avatar initials from a customer name. */
export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
