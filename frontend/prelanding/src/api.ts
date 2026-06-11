// Klien API Aegis (session/init + score). CORS lintas-origin; TANPA secret di klien.

import { apiBase, SCHEMA_VERSION } from "./config";
import type { Params } from "./params";
import type { Signals } from "./signals";

export interface ApiError {
  status: number;
  code: string;
  message: string;
}

export type Decision =
  | { decision: "allow"; redirect_url: string }
  | { decision: "block"; notice: string };

async function post<T>(path: string, body: unknown): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${apiBase()}${path}`, {
      method: "POST",
      mode: "cors",
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw <ApiError>{ status: 0, code: "network_error", message: "Gagal terhubung." };
  }
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw <ApiError>{
      status: resp.status,
      code: data?.code ?? "error",
      message: data?.message ?? "Terjadi kesalahan.",
    };
  }
  return data as T;
}

export function sessionInit(p: Params): Promise<{ session_token: string; expires_at: string }> {
  return post("/v1/session/init", {
    trx_id: p.trx_id,
    service: p.service,
    campaign: p.campaign,
    source: p.source,
    pub_id: p.pub_id,
    source_params: p.source_params,
  });
}

export function score(p: Params, token: string, signals: Signals): Promise<Decision> {
  return post("/v1/score", {
    trx_id: p.trx_id,
    service: p.service,
    campaign: p.campaign,
    source: p.source,
    pub_id: p.pub_id,
    source_params: p.source_params,
    session_token: token,
    schema_version: SCHEMA_VERSION,
    signals,
  });
}
