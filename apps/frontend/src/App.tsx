import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthProvider";
import { GuestOnly, OnboardingGate, RequireAuth, RequireOnboarding } from "@/auth/guards";
import { ProductTour } from "@/components/tour/ProductTour";
import { DemoModeProvider } from "@/demo/DemoContext";
import Analytics from "@/pages/Analytics";
import AuditTimelinePage from "@/pages/AuditTimeline";
import Dashboard from "@/pages/Dashboard";
import DashboardLayout from "@/pages/DashboardLayout";
import LandingPage from "@/pages/Landing";
import LoginPage from "@/pages/Login";
import OnboardingPage from "@/pages/Onboarding";
import OperationsStatusPage from "@/pages/OperationsStatus";
import RecoveryQueue from "@/pages/RecoveryQueue";
import SettingsPage from "@/pages/Settings";
import SignupPage from "@/pages/Signup";
import SimulatorLabPage from "@/pages/SimulatorLab";
import { ToastProvider } from "@/toast/ToastProvider";

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
        <AuthProvider>
          <ToastProvider>
            <DemoModeProvider>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route element={<GuestOnly />}>
                  <Route path="login" element={<LoginPage />} />
                  <Route path="signup" element={<SignupPage />} />
                </Route>
                <Route path="demo" element={<DashboardLayout />}>
                  <Route index element={<Navigate to="/demo/dashboard" replace />} />
                  <Route path="dashboard" element={<Dashboard />} />
                  <Route path="recovery-queue" element={<RecoveryQueue />} />
                  <Route path="analytics" element={<Analytics />} />
                  <Route path="audit" element={<AuditTimelinePage />} />
                  <Route path="simulator" element={<SimulatorLabPage />} />
                  <Route path="operations" element={<OperationsStatusPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                </Route>
                <Route element={<RequireAuth />}>
                  <Route element={<OnboardingGate />}>
                    <Route path="onboarding" element={<OnboardingPage />} />
                  </Route>
                  <Route element={<RequireOnboarding />}>
                    <Route element={<DashboardLayout />}>
                      <Route path="dashboard" element={<Dashboard />} />
                      <Route path="recovery-queue" element={<RecoveryQueue />} />
                      <Route path="analytics" element={<Analytics />} />
                      <Route path="audit" element={<AuditTimelinePage />} />
                      <Route path="simulator" element={<SimulatorLabPage />} />
                      <Route path="operations" element={<OperationsStatusPage />} />
                      <Route path="settings" element={<SettingsPage />} />
                    </Route>
                  </Route>
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
              <ProductTour />
            </DemoModeProvider>
          </ToastProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
