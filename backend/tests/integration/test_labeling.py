"""AC-SVC-01.1/01.2: callback labeling idempoten + orphan (Postgres)."""

import uuid
from datetime import UTC, datetime

import psycopg
import pytest

from aegis.config import get_settings
from aegis.schemas.callback import ComplaintCallback, SubscriptionCallback
from aegis.services.labeling import record_complaint, record_subscription


def _reachable() -> bool:
    try:
        with psycopg.connect(get_settings().postgres_dsn, connect_timeout=3):
            return True
    except Exception:
        return False


def _trx() -> str:
    return f"trx-{uuid.uuid4().hex[:16]}"


def test_subscription_idempotent_and_orphan() -> None:
    if not _reachable():
        pytest.skip("PostgreSQL tak terjangkau")
    cb = SubscriptionCallback(
        event="subscription",
        trx_id=_trx(),
        charging_status="failed",
        charging_fail_reason="daily_limit_reached",
        service_id="SVC-1",
        msisdn_hash="deadbeef",
        event_time=datetime.now(UTC),
    )
    first = record_subscription(cb)
    assert first.stored and first.duplicate is False and first.orphan is True  # trx tak dikenal
    second = record_subscription(cb)
    assert second.duplicate is True  # idempoten


def test_complaint_idempotent_and_orphan() -> None:
    if not _reachable():
        pytest.skip("PostgreSQL tak terjangkau")
    cb = ComplaintCallback(event="complaint", trx_id=_trx(), event_time=datetime.now(UTC))
    first = record_complaint(cb)
    assert first.stored and first.orphan is True
    assert record_complaint(cb).duplicate is True
