"""Repository tabel `retrain_jobs` (T-15: catat trigger retrain; eksekusi worker = T-17)."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


def create_job(conn: psycopg.Connection, requested_by: str | None = None) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO retrain_jobs (requested_by) VALUES (%s::uuid) RETURNING id",
            (requested_by,),
        )
        return str(cur.fetchone()[0])


def get_job(conn: psycopg.Connection, job_id: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, status, metrics FROM retrain_jobs WHERE id = %s::uuid", (job_id,)
        )
        return cur.fetchone()


def mark_running(conn: psycopg.Connection, job_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE retrain_jobs SET status = 'running' WHERE id = %s::uuid", (job_id,)
        )


def mark_done(conn: psycopg.Connection, job_id: str, metrics: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE retrain_jobs SET status = 'done', metrics = %s, finished_at = now() "
            "WHERE id = %s::uuid",
            (Jsonb(metrics), job_id),
        )


def mark_failed(conn: psycopg.Connection, job_id: str, metrics: dict | None = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE retrain_jobs SET status = 'failed', metrics = %s, finished_at = now() "
            "WHERE id = %s::uuid",
            (Jsonb(metrics or {}), job_id),
        )
