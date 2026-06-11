"""Session token sekali-pakai pre-landing→scoring (`03 §2.1`).

Ditandatangani server (HMAC, key dari .env), terikat `trx_id`, TTL 10–15 mnt,
**single-use** (nonce di Redis dihapus saat dipakai → replay gagal). Tak ada secret di client.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from aegis.config import get_settings
from aegis.db.redis import get_redis

SESSION_TTL_SECONDS = 900  # 15 menit
_PREFIX = "session:"


class SessionTokenError(Exception):
    """Token invalid/kedaluwarsa/sudah dipakai/mismatch trx_id."""


def _sign(payload_b64: str, key: str) -> str:
    return hmac.new(key.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()


def issue(trx_id: str, service: str, campaign: str) -> tuple[str, datetime]:
    """Terbitkan token terikat (trx_id, service, campaign) — D3 (T-21, F-16)."""
    s = get_settings()
    jti = secrets.token_urlsafe(16)
    exp = datetime.now(UTC) + timedelta(seconds=SESSION_TTL_SECONDS)
    payload = {
        "trx_id": trx_id, "service": service, "campaign": campaign,
        "jti": jti, "exp": int(exp.timestamp()),
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).decode()
    token = f"{payload_b64}.{_sign(payload_b64, s.session_signing_key)}"
    get_redis().set(_PREFIX + jti, trx_id, ex=SESSION_TTL_SECONDS)
    return token, exp


def verify_and_consume(token: str, trx_id: str, service: str, campaign: str) -> None:
    """Validasi & langsung pakai token (single-use). Raise SessionTokenError bila gagal.

    Cek (trx_id, service, campaign) cocok dengan saat init (D3 — cegah token lintas-campaign).
    """
    s = get_settings()
    try:
        payload_b64, sig = token.split(".", 1)
    except ValueError as exc:
        raise SessionTokenError("malformed") from exc
    if not hmac.compare_digest(_sign(payload_b64, s.session_signing_key), sig):
        raise SessionTokenError("bad signature")
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64.encode()))
    except (ValueError, json.JSONDecodeError) as exc:
        raise SessionTokenError("bad payload") from exc
    if payload.get("trx_id") != trx_id:
        raise SessionTokenError("trx mismatch")
    if payload.get("service") != service or payload.get("campaign") != campaign:
        raise SessionTokenError("service/campaign mismatch")
    if int(payload.get("exp", 0)) < int(datetime.now(UTC).timestamp()):
        raise SessionTokenError("expired")
    # single-use: delete mengembalikan jumlah yang dihapus; 0 = sudah dipakai/kedaluwarsa
    if not get_redis().delete(_PREFIX + payload.get("jti", "")):
        raise SessionTokenError("already used or expired")
