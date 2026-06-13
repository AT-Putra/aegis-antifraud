"""Backfill sekali-jalan: salin outcomes & feedback (OLTP) → mirror OLAP (ADR-014).

Idempoten: tabel OLAP `outcome_log`/`feedback_log` = ReplacingMergeTree (dedup by ORDER BY),
jadi menjalankan ulang aman. Dipakai sekali saat deploy migrasi mirror.

Jalankan: `python -m aegis.jobs.backfill_olap_mirror` (di dalam container api), atau
`make backfill-olap`.
"""

from __future__ import annotations

import logging

from psycopg.rows import dict_row

from aegis.db.olap import outcome_repo
from aegis.db.postgres import connection

_log = logging.getLogger("aegis.backfill")


def backfill_outcomes() -> int:
    """Salin seluruh outcomes OLTP → outcome_log OLAP. Return jumlah baris dikirim."""
    n = 0
    with connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT trx_id, callback_type, charging_status, charging_fail_reason, received_at "
            "FROM outcomes"
        )
        for r in cur:
            outcome_repo.write_outcome(
                trx_id=r["trx_id"],
                callback_type=r["callback_type"],
                charging_status=r["charging_status"],
                charging_fail_reason=r["charging_fail_reason"],
                received_at=r["received_at"],
            )
            n += 1
    return n


def backfill_feedback() -> int:
    """Salin feedback OLTP yang sudah di-review (status != 'pending') → feedback_log OLAP.

    version = epoch detik created_at (monoton cukup utk backfill; review live pakai time_ns).
    """
    n = 0
    with connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, trx_id, flagged_label, review_status, created_at "
            "FROM feedback WHERE review_status <> 'pending'"
        )
        for r in cur:
            outcome_repo.write_feedback(
                id=str(r["id"]),
                trx_id=r["trx_id"],
                flagged_label=r["flagged_label"],
                review_status=r["review_status"],
                version=int(r["created_at"].timestamp()),
                created_at=r["created_at"],
            )
            n += 1
    return n


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    o = backfill_outcomes()
    f = backfill_feedback()
    _log.info("backfill OLAP mirror selesai: %d outcomes, %d feedback", o, f)
    print(f"backfill OLAP mirror: {o} outcomes, {f} feedback")


if __name__ == "__main__":
    main()
