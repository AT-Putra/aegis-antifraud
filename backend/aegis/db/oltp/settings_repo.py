"""Repository tabel `app_settings` (T-15: pengaturan global, mis. default_timezone)."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row


def list_all(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT key, value FROM app_settings ORDER BY key")
        return cur.fetchall()


def upsert(
    conn: psycopg.Connection, key: str, value: str, updated_by: str | None = None
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO app_settings (key, value, updated_by, updated_at) "
            "VALUES (%s, %s, %s::uuid, now()) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, "
            "updated_by = EXCLUDED.updated_by, updated_at = now()",
            (key, value, updated_by),
        )
