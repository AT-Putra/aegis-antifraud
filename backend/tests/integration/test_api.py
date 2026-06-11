"""AC-API-01..04: session/init, score (allow/block/502), callback (HMAC, replay)."""

import json
import uuid
from datetime import UTC, datetime

import psycopg
import pytest
from fastapi.testclient import TestClient

from aegis.config import get_settings
from aegis.cp.client import MintResult
from aegis.registry.service import register_service
from aegis.security.hmac_auth import compute_signature


def _reachable() -> bool:
    try:
        with psycopg.connect(get_settings().postgres_dsn, connect_timeout=3):
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _reachable(), reason="PostgreSQL tak terjangkau")


@pytest.fixture
def client():
    from aegis.main import app

    with TestClient(app) as c:
        yield c


def _service() -> str:
    slug = f"svc-{uuid.uuid4().hex[:12]}"
    register_service(slug, "Test", "TelcoX", "https://cp.example/req", "secret-key")
    return slug


_HUMAN = {
    "fingerprint": {"canvas_hash": "c1", "webgl": {"renderer": "Mali"},
                    "browser_environment": {"is_webview": False}},
    "behavior": {"mouse": {"move_count": 120, "velocity_mean": 1.2},
                 "touch": {"tap_count": 3}, "timing": {"interaction_count": 8}},
    "automation_hints": {"webdriver": False},
    "integrity": {"ever_visible": True},
}
_BOT = {
    "fingerprint": {"canvas_hash": "c1", "browser_environment": {"is_webview": True}},
    "behavior": {"mouse": {"move_count": 0}},
    "automation_hints": {"webdriver": True},
}


def _token(client, trx, service) -> str:
    r = client.post("/v1/session/init", json={"trx_id": trx, "service": service})
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


def test_session_init_unknown_service(client) -> None:
    svc = _service()
    assert client.post("/v1/session/init", json={"trx_id": "t1", "service": svc}).status_code == 200
    r = client.post("/v1/session/init", json={"trx_id": "t2", "service": "nope-xyz"})
    assert r.status_code == 404 and r.json()["code"] == "service_not_found"


def test_score_allow_mint(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "aegis.api.scoring.mint_weboptin_url",
        lambda *a, **k: MintResult("minted", redirect_url="https://telco/x?token=1", host="telco"),
    )
    svc = _service()
    trx = f"trx-{uuid.uuid4().hex[:12]}"
    tok = _token(client, trx, svc)
    r = client.post("/v1/score", json={
        "trx_id": trx, "service": svc, "session_token": tok,
        "schema_version": "1.0", "signals": _HUMAN,
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["decision"] == "allow" and body["redirect_url"].endswith("token=1")


def test_score_block_hard_rule(client) -> None:
    svc = _service()
    trx = f"trx-{uuid.uuid4().hex[:12]}"
    tok = _token(client, trx, svc)
    r = client.post("/v1/score", json={
        "trx_id": trx, "service": svc, "session_token": tok,
        "schema_version": "1.0", "signals": _BOT,
    })
    assert r.status_code == 200
    assert r.json()["decision"] == "block"
    assert "final_score" not in r.json()  # skor tak diekspos


def test_score_weboptin_unavailable(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "aegis.api.scoring.mint_weboptin_url",
        lambda *a, **k: MintResult("failed", reason="cp_error"),
    )
    svc = _service()
    trx = f"trx-{uuid.uuid4().hex[:12]}"
    tok = _token(client, trx, svc)
    r = client.post("/v1/score", json={
        "trx_id": trx, "service": svc, "session_token": tok,
        "schema_version": "1.0", "signals": _HUMAN,
    })
    assert r.status_code == 502 and r.json()["code"] == "weboptin_unavailable"


def test_callback_billing_hmac_and_invalid(client) -> None:
    secret = get_settings().billing_hmac_secret
    body = json.dumps({
        "event": "complaint",
        "trx_id": f"trx-{uuid.uuid4().hex[:12]}",
        "event_time": datetime.now(UTC).isoformat(),
    })
    ts = datetime.now(UTC).isoformat()
    sig = compute_signature(secret, ts, body)
    ok = client.post("/v1/callback/billing", content=body, headers={
        "X-Aegis-Timestamp": ts, "X-Aegis-Signature": sig, "Content-Type": "application/json",
    })
    assert ok.status_code == 200 and ok.json()["status"] == "ok"

    bad = client.post("/v1/callback/billing", content=body, headers={
        "X-Aegis-Timestamp": ts, "X-Aegis-Signature": "deadbeef",
        "Content-Type": "application/json",
    })
    assert bad.status_code == 401
