import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LogOut, Settings, UserRound } from "lucide-react";
import { useAuth } from "@/auth/AuthProvider";
import { DemoBadge } from "@/demo/DemoBadge";
import { useDemoMode } from "@/demo/DemoContext";
import { loadAvatarDataUrl } from "@/lib/workspacePrefs";

function initials(name: string, email: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
  }
  if (parts[0]) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase() || "RP";
}

/** Profile menu in the merchant navbar. */
export function ProfileMenu() {
  const { user, logout } = useAuth();
  const { isDemo, opsPath } = useDemoMode();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const avatar = loadAvatarDataUrl();

  useEffect(() => {
    function onDoc(event: MouseEvent) {
      if (root.current && !root.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  if (!user && isDemo) {
    return (
      <Link
        to="/"
        className="rounded-lg border border-border px-2.5 py-1 text-xs text-muted hover:text-foreground"
      >
        Exit demo
      </Link>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="relative" ref={root}>
      <button
        type="button"
        className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full bg-ai-muted text-xs font-semibold text-ai"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        onClick={() => setOpen((value) => !value)}
      >
        {avatar ? <img src={avatar} alt="" className="h-full w-full object-cover" /> : initials(user.full_name, user.email)}
      </button>
      {open ? (
        <div
          role="menu"
          className="absolute right-0 z-30 mt-2 w-56 rounded-xl border border-border bg-surface p-2 shadow-[var(--shadow-card)]"
        >
          <p className="flex items-center gap-2 truncate px-2 py-1 text-sm font-medium">
            {user.full_name}
            {user.workspace_kind === "demo" ? <DemoBadge compact /> : null}
          </p>
          <p className="truncate px-2 pb-2 text-xs text-muted">{user.email}</p>
          <Link
            to={opsPath("/settings")}
            role="menuitem"
            className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-surface-hover"
            onClick={() => setOpen(false)}
          >
            <Settings size={14} aria-hidden />
            Settings
          </Link>
          <Link
            to={opsPath("/operations")}
            role="menuitem"
            className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-surface-hover"
            onClick={() => setOpen(false)}
          >
            <UserRound size={14} aria-hidden />
            Operations
          </Link>
          <button
            type="button"
            role="menuitem"
            className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-blocked hover:bg-surface-hover"
            onClick={() => {
              setOpen(false);
              void logout().then(() => navigate("/", { replace: true }));
            }}
          >
            <LogOut size={14} aria-hidden />
            Sign out
          </button>
        </div>
      ) : null}
    </div>
  );
}
