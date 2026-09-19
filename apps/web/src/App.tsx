import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./state/auth";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { DashboardPage } from "./pages/DashboardPage";
import { NewSessionPage } from "./pages/NewSessionPage";
import { SessionPage } from "./pages/SessionPage";
import { MockInterviewPage } from "./pages/MockInterviewPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { ResumesPage } from "./pages/ResumesPage";
import { SessionsPage } from "./pages/SessionsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { BillingPage } from "./pages/BillingPage";
import { HelpPage } from "./pages/HelpPage";
import { AppShell } from "./components/AppShell";

function Private({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center text-mist" role="status">
        Loading InterviewPilot AI…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <AppShell>{children}</AppShell>;
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/landing" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/dashboard" element={<Private><DashboardPage /></Private>} />
      <Route path="/session/new" element={<Private><NewSessionPage /></Private>} />
      <Route path="/session/:id" element={<Private><SessionPage /></Private>} />
      <Route path="/mock-interview" element={<Private><MockInterviewPage /></Private>} />
      <Route path="/documents" element={<Private><DocumentsPage /></Private>} />
      <Route path="/resumes" element={<Private><ResumesPage /></Private>} />
      <Route path="/sessions" element={<Private><SessionsPage /></Private>} />
      <Route path="/settings" element={<Private><SettingsPage /></Private>} />
      <Route path="/billing" element={<Private><BillingPage /></Private>} />
      <Route path="/help" element={<Private><HelpPage /></Private>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
