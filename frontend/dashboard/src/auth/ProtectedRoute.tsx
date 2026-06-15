// Guard rute: wajib login; opsional batasi role admin.
// ADR-015: role di-bootstrap async (GET /users/me) → tunggu `loading` sebelum redirect,
// agar reload tidak salah lempar ke /login saat sesi sebenarnya masih valid.
import { Center, Loader } from "@mantine/core";
import { Navigate, Outlet } from "react-router-dom";

import type { Role } from "../api/types";
import { useAuth } from "./AuthContext";

export function ProtectedRoute({ requireRole }: { requireRole?: Role }) {
  const { isAuthed, role, loading } = useAuth();
  if (loading) {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }
  if (!isAuthed) return <Navigate to="/login" replace />;
  if (requireRole && role !== requireRole) return <Navigate to="/" replace />;
  return <Outlet />;
}
