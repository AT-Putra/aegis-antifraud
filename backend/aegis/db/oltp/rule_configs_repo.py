"""Repository tabel `rule_configs` (versioned). T-11: ambil konfigurasi aktif."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row


def get_active(conn: psycopg.Connection) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT version, params, threshold, blend_weights "
            "FROM rule_configs WHERE active ORDER BY version DESC LIMIT 1"
        )
        return cur.fetchone()
