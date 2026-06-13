"""Mirror outcomes & feedback ke ClickHouse (OLAP) untuk statistik full-OLAP (ADR-014).

Loss-tolerant (async_insert): sumber kebenaran tetap OLTP (`outcomes`/`feedback`); ini cermin
agar agregat dashboard (fraud_est/complaints/charging) lepas dari jalur tulis panas OLTP.
Dual-write dipanggil best-effort dari service (try/except) — kegagalan OLAP tak menggagalkan
callback/review.
"""

from __future__ import annotations

import clickhouse_connect

from aegis.config import Settings, get_settings

_ASYNC = {"async_insert": 1, "wait_for_async_insert": 0}
_client = None


def _get_client(s: Settings):
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=s.clickhouse_host,
            port=s.clickhouse_port,
            username=s.clickhouse_user,
            password=s.clickhouse_password,
            database=s.clickhouse_db,
        )
    return _client


def write_outcome(
    *,
    trx_id: str,
    callback_type: str,
    charging_status: str | None,
    charging_fail_reason: str | None,
    received_at=None,
    settings: Settings | None = None,
) -> None:
    """Cermin satu baris outcomes ke `outcome_log`. received_at None → default now() server."""
    s = settings or get_settings()
    client = _get_client(s)
    cols = ["trx_id", "callback_type", "charging_status", "charging_fail_reason"]
    row = [trx_id, callback_type, charging_status or "", charging_fail_reason or ""]
    if received_at is not None:
        cols.append("received_at")
        row.append(received_at)
    client.insert("outcome_log", [row], column_names=cols, settings=_ASYNC)


def write_feedback(
    *,
    id: str,
    trx_id: str | None,
    flagged_label: str,
    review_status: str,
    version: int,
    created_at=None,
    settings: Settings | None = None,
) -> None:
    """Cermin feedback yang sudah di-review ke `feedback_log`. version = penentu baris terbaru."""
    s = settings or get_settings()
    client = _get_client(s)
    cols = ["id", "trx_id", "flagged_label", "review_status", "version"]
    row = [id, trx_id or "", flagged_label, review_status, int(version)]
    if created_at is not None:
        cols.append("created_at")
        row.append(created_at)
    client.insert("feedback_log", [row], column_names=cols, settings=_ASYNC)
