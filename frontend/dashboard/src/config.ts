// Base URL API. Same-origin default (dashboard disajikan Caddy bersama /v1).
declare global {
  interface Window {
    AEGIS_CONFIG?: { apiBase?: string };
  }
}

export function apiBase(): string {
  const runtime = typeof window !== "undefined" ? window.AEGIS_CONFIG?.apiBase : undefined;
  const built = import.meta.env?.VITE_AEGIS_API_BASE as string | undefined;
  return (runtime || built || "").replace(/\/+$/, "");
}
