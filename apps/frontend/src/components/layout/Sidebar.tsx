import {
  Activity,
  BarChart3,
  FlaskConical,
  History,
  LayoutDashboard,
  ListTodo,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { DemoBadge } from "@/demo/DemoBadge";
import { useDemoMode } from "@/demo/DemoContext";

const ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/recovery-queue", label: "Recovery Queue", icon: ListTodo, end: false },
  { to: "/analytics", label: "Analytics", icon: BarChart3, end: false },
  { to: "/audit", label: "Audit Timeline", icon: History, end: false },
  { to: "/simulator", label: "Simulator", icon: FlaskConical, end: false },
  { to: "/operations", label: "Operations", icon: Activity, end: false },
] as const;

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

/** Collapsible merchant operations sidebar. */
export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const { isDemo, opsPath } = useDemoMode();

  return (
    <aside
      className={`flex h-screen shrink-0 flex-col border-r border-border bg-canvas-muted transition-[width] duration-200 ${
        collapsed ? "w-[72px]" : "w-56"
      }`}
      aria-label="Primary"
    >
      <div className="flex h-16 items-center justify-between gap-2 border-b border-border px-3">
        {!collapsed ? (
          <div className="min-w-0">
            <p className="flex items-center gap-2 truncate text-sm font-semibold text-foreground">
              RecoveryPilot
              {isDemo ? <DemoBadge compact /> : null}
            </p>
            <p className="truncate text-[11px] text-muted">{isDemo ? "FitLife seed-42" : "Merchant ops"}</p>
          </div>
        ) : (
          <span className="mx-auto text-sm font-semibold text-ai">RP</span>
        )}
        <button
          type="button"
          onClick={onToggle}
          className="rounded-lg p-1.5 text-muted hover:bg-surface-hover hover:text-foreground"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-expanded={!collapsed}
        >
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-2">
        {ITEMS.map((item) => {
          const Icon = item.icon;
          const to = opsPath(item.to);
          return (
            <NavLink
              key={item.to}
              to={to}
              end={item.end}
              title={item.label}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors duration-150 ${
                  isActive
                    ? "bg-surface-hover text-foreground"
                    : "text-muted hover:bg-surface hover:text-foreground"
                } ${collapsed ? "justify-center px-2" : ""}`
              }
            >
              <Icon size={18} aria-hidden />
              {!collapsed ? <span>{item.label}</span> : <span className="sr-only">{item.label}</span>}
            </NavLink>
          );
        })}
        <NavLink
          to={opsPath("/settings")}
          title="Settings"
          className={({ isActive }) =>
            `mt-auto flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors duration-150 ${
              isActive
                ? "bg-surface-hover text-foreground"
                : "text-muted hover:bg-surface hover:text-foreground"
            } ${collapsed ? "justify-center px-2" : ""}`
          }
        >
          <Settings size={18} aria-hidden />
          {!collapsed ? <span>Settings</span> : <span className="sr-only">Settings</span>}
        </NavLink>
      </nav>
    </aside>
  );
}
