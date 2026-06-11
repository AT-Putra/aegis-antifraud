"""AC-SVC-01.3: feedback submit → review accepted → jadi label (Postgres)."""

import uuid

import psycopg
import pytest

from aegis.config import get_settings
from aegis.services.feedback import (
    accepted_labels,
    list_pending,
    review_feedback,
    submit_feedback,
)


def _reachable() -> bool:
    try:
        with psycopg.connect(get_settings().postgres_dsn, connect_timeout=3):
            return True
    except Exception:
        return False


def test_feedback_flow_accepted_becomes_label() -> None:
    if not _reachable():
        pytest.skip("PostgreSQL tak terjangkau")
    trx = f"trx-{uuid.uuid4().hex[:16]}"
    fid = submit_feedback(flagged_label="robot", trx_id=trx, note="mencurigakan")
    assert fid

    assert trx in {f["trx_id"] for f in list_pending()}  # status pending

    row = review_feedback(fid, "accepted")
    assert row is not None and row["review_status"] == "accepted"

    assert trx in {label["trx_id"] for label in accepted_labels()}  # jadi label retraining
