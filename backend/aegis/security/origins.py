"""Whitelist origin pre-landing (`03 §8`).

Rilis-1 (F-16, T-21): **CORS per-campaign** — origin sah = whitelist global (`app_settings`/env,
untuk dashboard/non-campaign) ∪ union `allowed_origins` semua campaign aktif (pre-landing
portabel). Union campaign di-cache (TTL pendek) agar tak query DB tiap request (D1).
"""

from __future__ import annotations

import time

from aegis.config import get_settings

_CACHE_TTL = 60.0
_origins_cache: tuple[float, frozenset[str]] | None = None


def allowed_origins() -> list[str]:
    raw = get_settings().allowed_origins
    return [o.strip() for o in raw.split(",") if o.strip()]


def is_allowed_origin(origin: str | None) -> bool:
    """Whitelist GLOBAL saja (dashboard/non-campaign)."""
    return bool(origin) and origin in allowed_origins()


def _campaign_origins() -> frozenset[str]:
    """Union allowed_origins campaign aktif, di-cache TTL pendek. Gagal → set kosong."""
    global _origins_cache
    now = time.monotonic()
    if _origins_cache is not None and now - _origins_cache[0] < _CACHE_TTL:
        return _origins_cache[1]
    try:
        from aegis.db.oltp import campaigns_repo
        from aegis.db.postgres import connection

        with connection() as conn:
            origins = frozenset(campaigns_repo.active_origins(conn))
    except Exception:
        origins = _origins_cache[1] if _origins_cache else frozenset()
    _origins_cache = (now, origins)
    return origins


def is_allowed_dynamic(origin: str | None) -> bool:
    """Sah bila ∈ whitelist global ATAU ∈ union origin campaign aktif (untuk CORS browser)."""
    if not origin:
        return False
    return origin in allowed_origins() or origin in _campaign_origins()


def invalidate_cache() -> None:
    """Reset cache (dipanggil setelah create/update campaign)."""
    global _origins_cache
    _origins_cache = None
