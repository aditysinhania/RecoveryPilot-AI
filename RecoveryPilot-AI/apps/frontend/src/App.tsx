import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import Analytics from "@/pages/Analytics";
import AuditTimelinePage from "@/pages/AuditTimeline";
import Dashboard from "@/pages/Dashboard";
import DashboardLayout from "@/pages/DashboardLayout";
import SimulatorLabPage from "@/pages/SimulatorLab";
import RecoveryQueue from "@/pages/RecoveryQueue";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<DashboardLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="recovery-queue" element={<RecoveryQueue />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="audit" element={<AuditTimelinePage />} />
            <Route path="simulator" element={<SimulatorLabPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
