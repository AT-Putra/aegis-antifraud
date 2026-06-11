"""HMAC-SHA256 untuk kanal server-to-server: inbound billing & outbound CP.

Tanda tangan atas `timestamp + raw_body`; anti-replay 15 menit; compare constant-time.
(`03 §2.1/§4/§5`, ADR-010)
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime

REPLAY_WINDOW_SECONDS = 900  # 15 menit


def compute_signature(secret: str, timestamp: str, raw_body: str | bytes) -> str:
    body = raw_body.encode() if isinstance(raw_body, str) else raw_body
    return hmac.new(secret.encode(), timestamp.encode() + body, hashlib.sha256).hexdigest()


def sign_outbound(secret: str, timestamp: str, raw_body: str | bytes) -> str:
    """Tanda tangani request Aegis→CP (X-Aegis-Signature)."""
    return compute_signature(secret, timestamp, raw_body)


def _timestamp_fresh(timestamp: str, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    try:
        ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return abs((now - ts).total_seconds()) <= REPLAY_WINDOW_SECONDS


def verify_inbound(
    secret: str, timestamp: str, raw_body: str | bytes, signature: str,
    now: datetime | None = None,
) -> bool:
    """Verifikasi callback billing: cek window anti-replay lalu signature (constant-time)."""
    if not _timestamp_fresh(timestamp, now):
        return False
    expected = compute_signature(secret, timestamp, raw_body)
    return hmac.compare_digest(expected, signature)
