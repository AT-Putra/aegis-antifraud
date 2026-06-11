"""Repository tabel `rule_configs` (versioned). T-11: ambil aktif; T-15: versi & PUT."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def get_active(conn: psycopg.Connection) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT version, params, threshold, blend_weights, defaults_range_meta "
            "FROM rule_configs WHERE active ORDER BY version DESC LIMIT 1"
        )
        return cur.fetchone()


def list_versions(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT version, created_by, created_at, active "
            "FROM rule_configs ORDER BY version DESC"
        )
        return cur.fetchall()


def insert_version(
    conn: psycopg.Connection,
    *,
    params: dict,
    threshold: float,
    blend_weights: dict,
    defaults_range_meta: dict | None = None,
    created_by: str | None = None,
) -> int:
    """PUT config: nonaktifkan semua, sisipkan versi = max+1 aktif. Kembalikan versi baru.

    Pemanggil menjalankan dalam satu `connection()` (transaksi) → atomic (AC-ADMIN-01).
    """
    with conn.cursor() as cur:
        cur.execute("UPDATE rule_configs SET active = false WHERE active")
        cur.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM rule_configs")
        new_version = int(cur.fetchone()[0])
        cur.execute(
            "INSERT INTO rule_configs "
            "(version, params, threshold, blend_weights, defaults_range_meta, active, created_by) "
            "VALUES (%s, %s, %s, %s, %s, true, %s::uuid)",
            (
                new_version,
                Jsonb(params),
                threshold,
                Jsonb(blend_weights),
                Jsonb(defaults_range_meta or {}),
                created_by,
            ),
        )
        return new_version
