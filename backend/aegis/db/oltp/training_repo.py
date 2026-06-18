"""Sumber label retraining (T-17): gabung `decisions`+`outcomes` per-trx (ground truth).

Hanya keputusan yang sampai billing punya sinyal label. `block` dikecualikan (tak ada
ground truth). Maturation & override feedback diterapkan di `jobs/retrain.py`.
"""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row


def labeled_candidates(conn: psycopg.Connection) -> list[dict]:
    """Per-trx: subscription_success, has_complaint, ref_time (waktu acuan maturation).

    ref_time = received_at callback subscription bila ada, fallback decisions.created_at.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT d.trx_id, "
            "  bool_or(o.callback_type = 'subscription' AND o.charging_status = 'success') "
            "    AS subscription_success, "
            "  bool_or(o.callback_type = 'complaint') AS has_complaint, "
            "  max(o.charging_fail_reason) FILTER ("
            "    WHERE o.callback_type = 'subscription' AND o.charging_status <> 'success') "
            "    AS charging_fail_reason, "
            "  COALESCE(min(o.received_at) FILTER (WHERE o.callback_type = 'subscription'), "
            "           d.created_at) AS ref_time "
            "FROM decisions d JOIN outcomes o ON o.trx_id = d.trx_id "
            "GROUP BY d.trx_id, d.created_at"
        )
        return cur.fetchall()
