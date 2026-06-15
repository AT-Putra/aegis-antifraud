// Auth state (ADR-015): role bukan dari localStorage (cookie httpOnly tak terbaca JS) →
// di-bootstrap via GET /users/me saat mount. login/logout = POST; auto-logout saat 401.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { api } from "../api/client";
import type { Me, Role } from "../api/types";

interface AuthState {
  role: Role | null;
  isAuthed: boolean;
  loading: boolean; // true selama bootstrap GET /users/me belum selesai
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role | null>(null);
  const [loading, setLoading] = useState(true);

  // Bootstrap: cookie httpOnly dikirim otomatis → /users/me menentukan sesi & role.
  useEffect(() => {
    let alive = true;
    api
      .get<Me>("/v1/users/me")
      .then((me) => alive && setRole(me.role))
      .catch(() => alive && setRole(null))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const onUnauthorized = () => setRole(null);
    window.addEventListener("aegis:unauthorized", onUnauthorized);
    return () => window.removeEventListener("aegis:unauthorized", onUnauthorized);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.post<{ role: Role }>("/v1/auth/login", { username, password });
    setRole(res.role);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/v1/auth/logout");
    } catch {
      /* tetap bersihkan state lokal walau request gagal */
    }
    setRole(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ role, isAuthed: !!role, loading, login, logout }),
    [role, loading, login, logout],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth di luar AuthProvider");
  return v;
}
