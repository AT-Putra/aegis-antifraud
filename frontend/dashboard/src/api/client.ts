// Klien HTTP (ADR-015): auth via cookie httpOnly `aegis_jwt` (dikirim otomatis dgn
// credentials:"include"). Mutasi melampirkan header X-CSRF-Token dari cookie non-httpOnly
// `aegis_csrf` (double-submit). 401 → event unauthorized (logout). Tak ada token di JS.
import { apiBase } from "../config";

const CSRF_COOKIE = "aegis_csrf";

/** Baca cookie non-httpOnly (mis. aegis_csrf). null bila tak ada. */
function readCookie(name: string): string | null {
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

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

const MUTATING = new Set(["POST", "PUT", "PATCH", "DELETE"]);

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  // CSRF double-submit: pantulkan cookie aegis_csrf via header pada mutasi.
  if (MUTATING.has(method)) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  const resp = await fetch(`${apiBase()}${path}`, {
    method,
    headers,
    credentials: "include", // kirim/terima cookie auth (same-origin via Caddy)
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (resp.status === 401) {
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
