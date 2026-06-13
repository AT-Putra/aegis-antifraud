"""Workflow feedback: user submit → admin review → accepted jadi label retraining (`03 §6`)."""

from __future__ import annotations

import logging
import time

from aegis.db.olap import outcome_repo
from aegis.db.oltp import feedback_repo
from aegis.db.postgres import connection

_log = logging.getLogger("aegis.feedback")


def submit_feedback(
    *,
    flagged_label: str,
    trx_id: str | None = None,
    decision_id: str | None = None,
    user_id: str | None = None,
    note: str | None = None,
) -> str:
    with connection() as conn:
        return feedback_repo.insert_feedback(
            conn,
            trx_id=trx_id,
            decision_id=decision_id,
            user_id=user_id,
            flagged_label=flagged_label,
            note=note,
        )


def review_feedback(
    feedback_id: str, review_status: str, reviewed_by: str | None = None
) -> dict | None:
    with connection() as conn:
        result = feedback_repo.update_review(conn, feedback_id, review_status, reviewed_by)
    # Mirror status final ke OLAP (statistik fraud_est). version=time_ns → review terbaru menang.
    # Best-effort & loss-tolerant (ADR-014).
    if result:
        try:
            outcome_repo.write_feedback(
                id=str(result["id"]),
                trx_id=result.get("trx_id"),
                flagged_label=result["flagged_label"],
                review_status=result["review_status"],
                version=time.time_ns(),
            )
        except Exception:  # noqa: BLE001 — OLAP loss-tolerant
            _log.warning("OLAP mirror feedback gagal: id=%s", feedback_id)
    return result


def list_pending() -> list[dict]:
    with connection() as conn:
        return feedback_repo.list_by_status(conn, "pending")


def accepted_labels() -> list[dict]:
    with connection() as conn:
        return feedback_repo.accepted_labels(conn)
