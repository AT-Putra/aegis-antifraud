"""Cache Redis write-through untuk riwayat device (fast-path lookup). K2.

Postgres tetap sumber kebenaran; cache mempercepat baca "device dikenal" + dipakai
sinyal velocity di features (T-05). TTL 1 hari.
"""

from __future__ import annotations

import json
from datetime import datetime

from aegis.db.redis import get_redis

_TTL_SECONDS = 86_400


def _key(device_id: str) -> str:
    return f"device:{device_id}"


def get_cached(device_id: str) -> dict | None:
    raw = get_redis().get(_key(device_id))
    return json.loads(raw) if raw else None


def write_through(
    device_id: str, event_count: int, first_seen: datetime, last_seen: datetime
) -> None:
    get_redis().set(
        _key(device_id),
        json.dumps(
            {
                "event_count": event_count,
                "first_seen": first_seen.isoformat(),
                "last_seen": last_seen.isoformat(),
            }
        ),
        ex=_TTL_SECONDS,
    )
