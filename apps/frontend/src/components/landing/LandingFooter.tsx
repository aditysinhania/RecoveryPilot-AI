import { Link } from "react-router-dom";
import { BrandMark } from "@/components/landing/BrandMark";

const COLUMNS = [
  {
    title: "Product",
    links: [
      { href: "#features", label: "Features" },
      { href: "#simulator", label: "Simulator" },
      { href: "#pricing", label: "Pricing" },
      { href: "/signup", label: "Start free trial", internal: true },
    ],
  },
  {
    title: "Company",
    links: [
      { href: "#trusted", label: "Merchants" },
      { href: "#insights", label: "AI insights" },
      { href: "#stories", label: "Stories" },
      { href: "/login", label: "Login", internal: true },
    ],
  },
  {
    title: "Resources",
    links: [
      { href: "#docs", label: "Docs" },
      { href: "#privacy", label: "Privacy" },
      { href: "#terms", label: "Terms" },
      { href: "#faq", label: "FAQ" },
    ],
  },
  {
    title: "Developers",
    links: [
      { href: "#docs", label: "API envelope" },
      { href: "#architecture", label: "Architecture" },
      { href: "https://github.com", label: "GitHub", external: true },
      { href: "https://www.linkedin.com", label: "LinkedIn", external: true },
    ],
  },
] as const;

/** Four-column marketing footer. */
export function LandingFooter() {
  return (
    <footer className="border-t border-white/10 bg-canvas-muted/80 py-14 text-sm">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 md:grid-cols-5">
        <div className="md:col-span-1">
          <div className="flex items-center gap-2">
            <BrandMark className="h-8 w-8" />
            <p className="font-semibold">RecoveryPilot</p>
          </div>
          <p className="mt-3 text-xs leading-5 text-muted">
            AI revenue recovery for Razorpay subscriptions. Integer paise. Asia/Kolkata default.
          </p>
        </div>
        {COLUMNS.map((column) => (
          <div key={column.title}>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">{column.title}</p>
            <ul className="mt-3 space-y-2">
              {column.links.map((link) => (
                <li key={link.label}>
                  {"internal" in link && link.internal ? (
                    <Link to={link.href} className="text-muted hover:text-foreground">
                      {link.label}
                    </Link>
                  ) : "external" in link && link.external ? (
                    <a href={link.href} className="text-muted hover:text-foreground" rel="noreferrer" target="_blank">
                      {link.label}
                    </a>
                  ) : (
                    <a href={link.href} className="text-muted hover:text-foreground">
                      {link.label}
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </footer>
  );
}
