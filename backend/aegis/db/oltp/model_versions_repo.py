"""Repository tabel `model_versions`. T-12: ambil aktif; T-15: list & aktivasi (approval)."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def get_active(conn: psycopg.Connection) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT version, algorithm, artifact_ref, calibration_ref "
            "FROM model_versions WHERE active ORDER BY version DESC LIMIT 1"
        )
        return cur.fetchone()


def next_version(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(version), 0) + 1 FROM model_versions")
        return int(cur.fetchone()[0])


def insert_version(
    conn: psycopg.Connection,
    *,
    version: int,
    algorithm: str,
    artifact_ref: str,
    calibration_ref: str | None,
    metrics: dict,
) -> dict:
    """Daftarkan model hasil retraining (T-17). active=false → butuh approval admin."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "INSERT INTO model_versions "
            "(version, algorithm, artifact_ref, calibration_ref, trained_at, metrics, active) "
            "VALUES (%s, %s, %s, %s, now(), %s, false) "
            "RETURNING id, version, algorithm, trained_at, metrics, active",
            (version, algorithm, artifact_ref, calibration_ref, Jsonb(metrics)),
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
