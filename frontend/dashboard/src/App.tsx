import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppLayout } from "./components/AppLayout";
import { DashboardPage } from "./pages/DashboardPage";
import { DecisionPage } from "./pages/DecisionPage";
import { LoginPage } from "./pages/LoginPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";
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
          <Route path="feedback" element={<PlaceholderPage title="Feedback" />} />
          <Route path="settings" element={<PlaceholderPage title="Pengaturan" />} />
          <Route element={<ProtectedRoute requireRole="admin" />}>
            <Route path="config" element={<PlaceholderPage title="Config" />} />
            <Route path="services" element={<PlaceholderPage title="Layanan" />} />
            <Route path="campaigns" element={<PlaceholderPage title="Campaign" />} />
            <Route path="users" element={<PlaceholderPage title="Users" />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
