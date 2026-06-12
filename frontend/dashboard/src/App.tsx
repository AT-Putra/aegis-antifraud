import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppLayout } from "./components/AppLayout";
import { CampaignsPage } from "./pages/CampaignsPage";
import { ConfigPage } from "./pages/ConfigPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DecisionPage } from "./pages/DecisionPage";
import { FeedbackPage } from "./pages/FeedbackPage";
import { LoginPage } from "./pages/LoginPage";
import { ModelsPage } from "./pages/ModelsPage";
import { ServicesPage } from "./pages/ServicesPage";
import { SettingsPage } from "./pages/SettingsPage";
import { UsersPage } from "./pages/UsersPage";
import { SearchPage } from "./pages/SearchPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="decision/:trxId" element={<DecisionPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route element={<ProtectedRoute requireRole="admin" />}>
            <Route path="config" element={<ConfigPage />} />
            <Route path="services" element={<ServicesPage />} />
            <Route path="campaigns" element={<CampaignsPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="feedback" element={<FeedbackPage />} />
            <Route path="models" element={<ModelsPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
