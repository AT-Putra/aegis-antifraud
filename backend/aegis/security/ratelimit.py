"""Rate-limit fixed-window berbasis Redis (TRD §7). Dipakai api init/score (T-12)."""

from __future__ import annotations

from aegis.db.redis import get_redis


def allow(key: str, limit: int, window_seconds: int) -> bool:
    """True bila masih dalam kuota. INCR + EXPIRE pada awal window."""
    r = get_redis()
    full = f"rl:{key}"
    current = r.incr(full)
    if current == 1:
        r.expire(full, window_seconds)
    return current <= limit
