// Klien HTTP: Bearer JWT dari localStorage; 401 → buang token (logout) + event.
import { apiBase } from "../config";

const TOKEN_KEY = "aegis_jwt";
const ROLE_KEY = "aegis_role";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  role: () => localStorage.getItem(ROLE_KEY),
  set: (jwt: string, role: string) => {
    localStorage.setItem(TOKEN_KEY, jwt);
    localStorage.setItem(ROLE_KEY, role);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function qs(params?: Record<string, unknown>): string {
  if (!params) return "";
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const resp = await fetch(`${apiBase()}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (resp.status === 401) {
    tokenStore.clear();
    window.dispatchEvent(new CustomEvent("aegis:unauthorized"));
    throw new ApiError(401, "unauthorized", "Sesi berakhir, masuk lagi.");
  }
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new ApiError(resp.status, data?.code ?? "error", data?.message ?? "Terjadi kesalahan.");
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, params?: Record<string, unknown>) => request<T>("GET", path + qs(params)),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body ?? {}),
};
