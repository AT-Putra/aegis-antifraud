// Parsing & sanitasi parameter URL pre-landing (03 §2 allowlist; AC-PL-03).

const TRX_ID = /^[A-Za-z0-9._:-]{1,128}$/;
const SLUG = /^[a-z0-9-]{1,64}$/;
const ATTR = /^[A-Za-z0-9._:-]{1,64}$/;

const KNOWN = new Set(["trx_id", "service", "campaign", "source", "pub_id"]);

export interface Params {
  trx_id: string;
  service: string;
  campaign: string;
  source: string | null;
  pub_id: string | null;
  source_params: Record<string, string>;
}

export class ParamError extends Error {}

export function parseParams(search: string): Params {
  const q = new URLSearchParams(search);

  const trx_id = q.get("trx_id") ?? "";
  const service = q.get("service") ?? "";
  const campaign = q.get("campaign") ?? "";
  if (!TRX_ID.test(trx_id)) throw new ParamError("trx_id tidak valid/absen");
  if (!SLUG.test(service)) throw new ParamError("service tidak valid/absen");
  if (!SLUG.test(campaign)) throw new ParamError("campaign tidak valid/absen");

  const source = clean(q.get("source"));
  const pub_id = clean(q.get("pub_id"));

  // Param tak dikenal yang lolos allowlist → source_params (diteruskan ke OLAP, D2).
  const source_params: Record<string, string> = {};
  for (const [k, v] of q.entries()) {
    if (KNOWN.has(k)) continue;
    if (ATTR.test(k) && v && v.length <= 256) source_params[k] = v;
  }

  return { trx_id, service, campaign, source, pub_id, source_params };
}

function clean(v: string | null): string | null {
  if (!v) return null;
  return ATTR.test(v) ? v : null; // nilai tak valid → diabaikan (nullable)
}
