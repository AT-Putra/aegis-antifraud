// Guard rute: wajib login; opsional batasi role admin.
import { Navigate, Outlet } from "react-router-dom";

import type { Role } from "../api/types";
import { useAuth } from "./AuthContext";

export function ProtectedRoute({ requireRole }: { requireRole?: Role }) {
  const { isAuthed, role } = useAuth();
  if (!isAuthed) return <Navigate to="/login" replace />;
  if (requireRole && role !== requireRole) return <Navigate to="/" replace />;
  return <Outlet />;
}
