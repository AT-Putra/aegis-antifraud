"""Repository tabel `feedback` (flag user → review admin → label retraining)."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row


def insert_feedback(
    conn: psycopg.Connection,
    *,
    trx_id: str | None,
    decision_id: str | None,
    user_id: str | None,
    flagged_label: str,
    note: str | None,
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO feedback (trx_id, decision_id, user_id, flagged_label, note) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (trx_id, decision_id, user_id, flagged_label, note),
        )
        return str(cur.fetchone()[0])


def update_review(
    conn: psycopg.Connection, feedback_id: str, review_status: str, reviewed_by: str | None
) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "UPDATE feedback SET review_status = %s, reviewed_by = %s WHERE id = %s::uuid "
            "RETURNING id, trx_id, flagged_label, review_status",
            (review_status, reviewed_by, feedback_id),
        )
        return cur.fetchone()


def list_by_status(conn: psycopg.Connection, status: str) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, trx_id, decision_id, flagged_label, note, review_status "
            "FROM feedback WHERE review_status = %s ORDER BY created_at",
            (status,),
        )
        return cur.fetchall()


def accepted_labels(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT trx_id, decision_id, flagged_label FROM feedback "
            "WHERE review_status = 'accepted'"
        )
        return cur.fetchall()
