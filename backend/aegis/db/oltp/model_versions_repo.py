"""Repository tabel `model_versions`. T-12: ambil aktif; T-15: list & aktivasi (approval)."""

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


def list_all(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, version, algorithm, trained_at, metrics, active "
            "FROM model_versions ORDER BY version DESC"
        )
        return cur.fetchall()


def activate(conn: psycopg.Connection, model_id: str) -> dict | None:
    """Aktivasi = approval admin (AC-RETRAIN-01.2). Atomic: nonaktifkan lain, aktifkan satu."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id FROM model_versions WHERE id = %s::uuid", (model_id,))
        if cur.fetchone() is None:
            return None
        cur.execute("UPDATE model_versions SET active = false WHERE active")
        cur.execute(
            "UPDATE model_versions SET active = true WHERE id = %s::uuid "
            "RETURNING id, version, algorithm, trained_at, metrics, active",
            (model_id,),
        )
        return cur.fetchone()
