"""Mint URL web-opt-in dari sistem CP (Aegis→CP, server-to-server). ADR-010, `03 §5`.

Decoupled: terima `cp_api_url` + `secret` sebagai argumen (tak impor registry/DB).
Anti-bypass: request ditandatangani HMAC per-service. Token mentah TIDAK disimpan
(hanya host untuk audit). Gagal/timeout → weboptin_status="failed" (system error, bukan fraud).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from aegis.schemas.cp import WebOptInRequest, WebOptInResponse
from aegis.security.hmac_auth import sign_outbound

_TIMEOUT_SECONDS = 5.0
_MAX_ATTEMPTS = 2  # 1 awal + 1 retry


@dataclass
class MintResult:
    weboptin_status: str  # "minted" | "failed"
    redirect_url: str | None = None
    host: str | None = None
    reason: str | None = None


def _build_signed_request(
    secret: str, trx_id: str, service: str, source: str | None, pub_id: str | None
) -> tuple[str, dict[str, str]]:
    req = WebOptInRequest(
        trx_id=trx_id,
        service=service,
        source=source,
        pub_id=pub_id,
        request_id=uuid4(),
        requested_at=datetime.now(UTC),
    )
    body = req.model_dump_json()  # byte-exact yang ditandatangani & dikirim
    ts = datetime.now(UTC).isoformat()
    headers = {
        "Content-Type": "application/json",
        "X-Aegis-Timestamp": ts,
        "X-Aegis-Signature": sign_outbound(secret, ts, body),
        "X-Aegis-Request-Id": str(req.request_id),
    }
    return body, headers


def mint_weboptin_url(
    cp_api_url: str,
    secret: str,
    *,
    trx_id: str,
    service: str,
    source: str | None = None,
    pub_id: str | None = None,
    client: httpx.Client | None = None,
) -> MintResult:
    body, headers = _build_signed_request(secret, trx_id, service, source, pub_id)
    own_client = client is None
    cl = client or httpx.Client(timeout=_TIMEOUT_SECONDS)
    last_reason = "unknown"
    try:
        for _ in range(_MAX_ATTEMPTS):
            try:
                resp = cl.post(cp_api_url, content=body, headers=headers)
            except httpx.HTTPError as exc:  # termasuk TimeoutException
                last_reason = f"network:{type(exc).__name__}"
                continue  # retry
            if resp.status_code >= 500:
                last_reason = f"http_{resp.status_code}"
                continue  # retry
            if resp.status_code != 200:
                return MintResult("failed", reason=f"http_{resp.status_code}")  # 4xx: no retry
            try:
                parsed = WebOptInResponse.model_validate_json(resp.content)
            except Exception:
                return MintResult("failed", reason="bad_response")
            if parsed.status != "ok" or not parsed.web_opt_in_url:
                return MintResult("failed", reason=parsed.reason or "cp_error")
            url = parsed.web_opt_in_url
            if not url.startswith("https://"):
                return MintResult("failed", reason="insecure_url")
            return MintResult("minted", redirect_url=url, host=urlparse(url).netloc)
        return MintResult("failed", reason=last_reason)
    finally:
        if own_client:
            cl.close()
