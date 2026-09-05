import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BrandMark } from "@/components/landing/BrandMark";
import { NAV_LINKS } from "@/components/landing/data";

interface LandingNavProps {
  signedIn: boolean;
  primaryTo: string;
  primaryLabel: string;
  onWatchDemo: () => void;
}

/** Sticky translucent marketing navbar. */
export function LandingNav({ signedIn, primaryTo, primaryLabel, onWatchDemo }: LandingNavProps) {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onScroll = (): void => {
      setScrolled(window.scrollY > 12);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={`sticky top-0 z-30 transition-colors duration-300 ${
        scrolled ? "border-b border-white/10 bg-canvas/70 backdrop-blur-xl" : "border-b border-transparent bg-transparent"
      }`}
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2">
          <BrandMark className="h-8 w-8" />
          <span className="text-sm font-semibold tracking-tight">RecoveryPilot</span>
        </Link>
        <nav className="hidden items-center gap-6 text-sm text-muted lg:flex">
          {NAV_LINKS.map((link) => (
            <a key={link.href} href={link.href} className="hover:text-foreground">
              {link.label}
            </a>
          ))}
        </nav>
        <div className="hidden items-center gap-2 lg:flex">
          {!signedIn ? (
            <Link to="/login" className="rounded-xl px-3 py-1.5 text-sm text-muted hover:text-foreground">
              Login
            </Link>
          ) : null}
          <Link to="/demo" className="rounded-xl px-3 py-1.5 text-sm text-ai hover:text-foreground">
            Try Live Demo
          </Link>
          <button type="button" className="rounded-xl px-3 py-1.5 text-sm text-muted hover:text-foreground" onClick={onWatchDemo}>
            Watch Demo
          </button>
          <Link to={primaryTo} className="landing-cta landing-cta-pulse rounded-2xl px-4 py-2 text-sm font-semibold text-canvas">
            {primaryLabel}
          </Link>
        </div>
        <button
          type="button"
          className="rounded-xl border border-border p-2 lg:hidden"
          aria-label={open ? "Close menu" : "Open menu"}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? <X size={16} /> : <Menu size={16} />}
        </button>
      </div>
      {open ? (
        <div className="border-t border-white/10 bg-canvas/95 px-4 py-3 lg:hidden">
          <nav className="flex flex-col gap-2 text-sm">
            {NAV_LINKS.map((link) => (
              <a key={link.href} href={link.href} className="py-1 text-muted" onClick={() => setOpen(false)}>
                {link.label}
              </a>
            ))}
            {!signedIn ? (
              <Link to="/login" className="py-1" onClick={() => setOpen(false)}>
                Login
              </Link>
            ) : null}
            <Link to="/demo" className="py-1 text-ai" onClick={() => setOpen(false)}>
              Try Live Demo
            </Link>
            <Link to={primaryTo} className="landing-cta mt-2 rounded-2xl px-4 py-2 text-center text-sm font-semibold text-canvas">
              {primaryLabel}
            </Link>
          </nav>
        </div>
      ) : null}
    </header>
  );
}
