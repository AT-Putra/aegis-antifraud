"""AC-SEC-02 & AC-SEC-03: HMAC inbound (billing) & outbound (CP)."""

from datetime import UTC, datetime, timedelta

from aegis.security.hmac_auth import compute_signature, sign_outbound, verify_inbound

_SECRET = "shared-secret"
_BODY = '{"event":"complaint","trx_id":"abc"}'


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def test_outbound_signature_deterministic() -> None:
    ts = "2026-06-11T08:00:00+00:00"
    a = sign_outbound(_SECRET, ts, _BODY)
    b = compute_signature(_SECRET, ts, _BODY)
    assert a == b and len(a) == 64  # hex sha256


def test_inbound_valid() -> None:
    ts = _now_iso()
    sig = compute_signature(_SECRET, ts, _BODY)
    assert verify_inbound(_SECRET, ts, _BODY, sig) is True


def test_inbound_bad_signature() -> None:
    ts = _now_iso()
    assert verify_inbound(_SECRET, ts, _BODY, "deadbeef") is False


def test_inbound_wrong_secret() -> None:
    ts = _now_iso()
    sig = compute_signature("other", ts, _BODY)
    assert verify_inbound(_SECRET, ts, _BODY, sig) is False


def test_inbound_stale_timestamp_rejected() -> None:
    ts = (datetime.now(UTC) - timedelta(minutes=20)).isoformat()
    sig = compute_signature(_SECRET, ts, _BODY)
    assert verify_inbound(_SECRET, ts, _BODY, sig) is False
