"""Repository tabel `model_versions`. T-12: ambil model aktif saat startup."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row


def get_active(conn: psycopg.Connection) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT version, algorithm, artifact_ref, calibration_ref "
            "FROM model_versions WHERE active ORDER BY version DESC LIMIT 1"
        )
        return cur.fetchone()
