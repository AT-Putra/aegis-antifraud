"""Workflow feedback: user submit → admin review → accepted jadi label retraining (`03 §6`)."""

from __future__ import annotations

from aegis.db.oltp import feedback_repo
from aegis.db.postgres import connection


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
        return feedback_repo.update_review(conn, feedback_id, review_status, reviewed_by)


def list_pending() -> list[dict]:
    with connection() as conn:
        return feedback_repo.list_by_status(conn, "pending")


def accepted_labels() -> list[dict]:
    with connection() as conn:
        return feedback_repo.accepted_labels(conn)
