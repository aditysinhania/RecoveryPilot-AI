import { createContext, useContext, useMemo, type ReactNode } from "react";
import { useLocation } from "react-router-dom";

interface DemoModeValue {
  isDemo: boolean;
  basePath: string;
  opsPath: (path: string) => string;
}

const DemoModeContext = createContext<DemoModeValue>({
  isDemo: false,
  basePath: "",
  opsPath: (path) => path,
});

/** Resolve an ops route under `/demo` when the live demo workspace is open. */
export function opsPathFor(isDemo: boolean, path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return isDemo ? `/demo${normalized}` : normalized;
}

/** Public demo workspace flag derived from the current URL. */
export function DemoModeProvider({ children }: { children: ReactNode }) {
  const { pathname } = useLocation();
  const isDemo = pathname === "/demo" || pathname.startsWith("/demo/");
  const value = useMemo<DemoModeValue>(
    () => ({
      isDemo,
      basePath: isDemo ? "/demo" : "",
      opsPath: (path: string) => opsPathFor(isDemo, path),
    }),
    [isDemo],
  );
  return <DemoModeContext.Provider value={value}>{children}</DemoModeContext.Provider>;
}

/** Whether the merchant chrome is running the unauthenticated FitLife demo. */
export function useDemoMode(): DemoModeValue {
  return useContext(DemoModeContext);
}
