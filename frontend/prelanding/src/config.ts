// Resolusi base URL API Aegis (portabilitas T-10).
// Prioritas: window.AEGIS_CONFIG (override runtime per-host) → build-env → same-origin.

declare global {
  interface Window {
    AEGIS_CONFIG?: { apiBase?: string };
  }
}

export function apiBase(): string {
  const runtime = typeof window !== "undefined" ? window.AEGIS_CONFIG?.apiBase : undefined;
  const built = import.meta.env?.VITE_AEGIS_API_BASE as string | undefined;
  const base = (runtime || built || "").trim();
  return base.replace(/\/+$/, ""); // tanpa trailing slash; "" = same-origin
}

export const SCHEMA_VERSION = "1.0";
