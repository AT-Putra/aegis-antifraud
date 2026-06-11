"""Repository tabel `devices` (TRD §3 db/oltp). Upsert dedup atomik."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

# (xmax = 0) → True bila baris baru di-INSERT; False bila ter-UPDATE via ON CONFLICT.
_UPSERT = """
INSERT INTO devices (device_id, fingerprint_hash, components_summary, event_count)
VALUES (%s, %s, %s, 1)
ON CONFLICT (device_id) DO UPDATE
    SET last_seen = now(), event_count = devices.event_count + 1
RETURNING event_count, first_seen, last_seen, (xmax = 0) AS is_new
"""


def upsert_device(
    conn: psycopg.Connection,
    device_id: str,
    fingerprint_hash: str,
    components_summary: dict[str, Any],
) -> tuple[bool, int, datetime, datetime]:
    """Insert device baru / increment event_count. Return (is_new, count, first_seen, last_seen)."""
    with conn.cursor() as cur:
        cur.execute(_UPSERT, (device_id, fingerprint_hash, Jsonb(components_summary)))
        event_count, first_seen, last_seen, is_new = cur.fetchone()
    return is_new, event_count, first_seen, last_seen
