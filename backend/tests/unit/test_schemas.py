"""AC-SCHEMA-01: Pydantic schema memvalidasi contoh payload `03`; menyimpang ditolak."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from aegis.schemas.callback import ComplaintCallback, SubscriptionCallback
from aegis.schemas.cp import WebOptInRequest, WebOptInResponse
from aegis.schemas.scoring import ScoreRequest, SessionInitRequest

_NOW = datetime(2026, 6, 11, 8, 0, tzinfo=UTC)


def test_session_init_valid() -> None:
    m = SessionInitRequest(trx_id="abc123", service="funzone", source="facebook", pub_id="123")
    assert m.service == "funzone"


def test_session_init_service_slug_invalid() -> None:
    with pytest.raises(ValidationError):
        SessionInitRequest(trx_id="abc", service="FunZone")  # huruf besar tak valid


def test_session_init_source_nullable() -> None:
    m = SessionInitRequest(trx_id="abc", service="funzone")
    assert m.source is None and m.pub_id is None


def test_score_request_valid() -> None:
    m = ScoreRequest(
        trx_id="abc123",
        service="funzone",
        session_token="tok",
        schema_version="1.0",
        signals={"fingerprint": {"canvas_hash": "x"}, "behavior": {}},
    )
    assert m.signals.fingerprint.canvas_hash == "x"


def test_score_request_bad_trx_id() -> None:
    with pytest.raises(ValidationError):
        ScoreRequest(
            trx_id="bad id!",  # spasi & '!' tak diizinkan
            service="funzone",
            session_token="tok",
            schema_version="1.0",
            signals={"fingerprint": {}, "behavior": {}},
        )


def test_score_request_missing_signals() -> None:
    with pytest.raises(ValidationError):
        ScoreRequest(trx_id="abc", service="funzone", session_token="t", schema_version="1.0")


def test_subscription_callback_valid() -> None:
    m = SubscriptionCallback(
        event="subscription",
        trx_id="abc",
        charging_status="failed",
        charging_fail_reason="daily_limit_reached",
        service_id="SVC-1",
        msisdn_hash="deadbeef",
        event_time=_NOW,
    )
    assert m.charging_fail_reason == "daily_limit_reached"


def test_subscription_callback_bad_reason() -> None:
    with pytest.raises(ValidationError):
        SubscriptionCallback(
            event="subscription", trx_id="abc", charging_status="failed",
            charging_fail_reason="unknown_reason", service_id="s", msisdn_hash="h", event_time=_NOW,
        )


def test_complaint_callback_valid() -> None:
    assert ComplaintCallback(event="complaint", trx_id="abc", event_time=_NOW).event == "complaint"


def test_weboptin_request_valid() -> None:
    m = WebOptInRequest(trx_id="abc", service="funzone", request_id=uuid4(), requested_at=_NOW)
    assert m.source is None


def test_weboptin_response_ok_and_error() -> None:
    assert WebOptInResponse(status="ok", web_opt_in_url="https://t/x?token=1").status == "ok"
    assert WebOptInResponse(status="error", reason="token_request_failed").reason
