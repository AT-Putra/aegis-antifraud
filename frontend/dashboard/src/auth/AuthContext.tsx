// Auth state: token+role di localStorage; login via /v1/auth/login; auto-logout saat 401.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { api, tokenStore } from "../api/client";
import type { Role } from "../api/types";

interface AuthState {
  role: Role | null;
  isAuthed: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role | null>(() => tokenStore.role() as Role | null);

  const logout = useCallback(() => {
    tokenStore.clear();
    setRole(null);
  }, []);

  useEffect(() => {
    const onUnauthorized = () => setRole(null);
    window.addEventListener("aegis:unauthorized", onUnauthorized);
    return () => window.removeEventListener("aegis:unauthorized", onUnauthorized);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.post<{ jwt: string; role: Role }>("/v1/auth/login", { username, password });
    tokenStore.set(res.jwt, res.role);
    setRole(res.role);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ role, isAuthed: !!role && !!tokenStore.get(), login, logout }),
    [role, login, logout],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth di luar AuthProvider");
  return v;
}
