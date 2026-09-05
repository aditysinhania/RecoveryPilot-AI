import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, X, XCircle } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ToastKind = "success" | "warning" | "error";

export interface ToastInput {
  kind: ToastKind;
  title: string;
  message?: string;
}

interface ToastItem extends ToastInput {
  id: string;
}

interface ToastContextValue {
  push: (input: ToastInput) => void;
  success: (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
  error: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const ICONS: Record<ToastKind, typeof CheckCircle2> = {
  success: CheckCircle2,
  warning: AlertTriangle,
  error: XCircle,
};

const TONE: Record<ToastKind, string> = {
  success: "border-recovered/40 bg-recovered-muted text-recovered",
  warning: "border-waiting/40 bg-waiting-muted text-waiting",
  error: "border-blocked/40 bg-blocked-muted text-blocked",
};

/** Bottom-right stacked toasts for merchant ops. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const push = useCallback(
    (input: ToastInput) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      setItems((current) => [...current.slice(-4), { ...input, id }]);
      window.setTimeout(() => dismiss(id), 5_200);
    },
    [dismiss],
  );

  const value = useMemo<ToastContextValue>(
    () => ({
      push,
      success: (title, message) => push({ kind: "success", title, message }),
      warning: (title, message) => push({ kind: "warning", title, message }),
      error: (title, message) => push({ kind: "error", title, message }),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed bottom-4 right-4 z-[70] flex w-[min(100%-2rem,22rem)] flex-col gap-2"
        aria-live="polite"
        aria-relevant="additions"
      >
        <AnimatePresence>
          {items.map((item) => {
            const Icon = ICONS[item.kind];
            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 12, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8 }}
                className={`pointer-events-auto flex gap-3 rounded-xl border px-3 py-2.5 shadow-[var(--shadow-card)] ${TONE[item.kind]}`}
                role="status"
              >
                <Icon size={16} className="mt-0.5 shrink-0" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-foreground">{item.title}</p>
                  {item.message ? <p className="mt-0.5 text-xs text-muted">{item.message}</p> : null}
                </div>
                <button
                  type="button"
                  className="shrink-0 rounded-md p-1 text-muted hover:text-foreground"
                  aria-label="Dismiss notification"
                  onClick={() => dismiss(item.id)}
                >
                  <X size={14} />
                </button>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

/** Global toast helpers. Must be used under ToastProvider. */
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}
