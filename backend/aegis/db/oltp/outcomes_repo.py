"""Repository tabel `outcomes` (label callback billing). Idempoten by (callback_type, trx_id)."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def insert_outcome(
    conn: psycopg.Connection,
    *,
    trx_id: str,
    callback_type: str,
    charging_status: str | None = None,
    charging_fail_reason: str | None = None,
    raw_payload: dict | None = None,
) -> bool:
    """True bila baris baru tersimpan; False bila duplikat (ON CONFLICT DO NOTHING)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO outcomes "
            "(trx_id, callback_type, charging_status, charging_fail_reason, raw_payload) "
            "VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (callback_type, trx_id) DO NOTHING RETURNING id",
            (
                trx_id,
                callback_type,
                charging_status,
                charging_fail_reason,
                Jsonb(raw_payload) if raw_payload is not None else None,
            ),
        )
        return cur.fetchone() is not None


def list_by_trx(conn: psycopg.Connection, trx_id: str) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT trx_id, callback_type, charging_status, charging_fail_reason "
            "FROM outcomes WHERE trx_id = %s",
            (trx_id,),
        )
        return cur.fetchall()
