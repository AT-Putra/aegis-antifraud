"""Repository tabel `decisions` (OLTP). Satu baris per request scoring."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row


def exists_by_trx(conn: psycopg.Connection, trx_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM decisions WHERE trx_id = %s", (trx_id,))
        return cur.fetchone() is not None


def get_by_trx(conn: psycopg.Connection, trx_id: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, trx_id, decision, final_score, weboptin_status "
            "FROM decisions WHERE trx_id = %s",
            (trx_id,),
        )
        return cur.fetchone()


def insert_decision(
    conn: psycopg.Connection,
    *,
    trx_id: str,
    device_id: str | None,
    service_id: str | None,
    source: str | None,
    pub_id: str | None,
    final_score: float | None,
    decision: str,
    threshold_used: float | None,
    rules_version: int | None,
    model_version: int | None,
    reason: str | None,
    weboptin_status: str,
    weboptin_host: str | None = None,
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO decisions "
            "(trx_id, device_id, service_id, source, pub_id, final_score, decision, "
            " threshold_used, rules_version, model_version, reason, weboptin_status, "
            " weboptin_host) "
            "VALUES (%s, %s, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING id",
            (
                trx_id,
                device_id,
                service_id,
                source,
                pub_id,
                final_score,
                decision,
                threshold_used,
                rules_version,
                model_version,
                reason,
                weboptin_status,
                weboptin_host,
            ),
        )
        return str(cur.fetchone()[0])


def update_weboptin(
    conn: psycopg.Connection, trx_id: str, weboptin_status: str, weboptin_host: str | None
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE decisions SET weboptin_status = %s, weboptin_host = %s WHERE trx_id = %s",
            (weboptin_status, weboptin_host, trx_id),
        )
