"""AC-E2E-01: journey penuh — scoring → keputusan → callback menyambung ke keputusan (US-02)."""

import json
import uuid
from datetime import UTC, datetime

import psycopg
import pytest
from fastapi.testclient import TestClient

from aegis.config import get_settings
from aegis.cp.client import MintResult
from aegis.db.oltp import decisions_repo, outcomes_repo
from aegis.db.postgres import connection
from aegis.registry.service import register_service
from aegis.security.hmac_auth import compute_signature


def _reachable() -> bool:
    try:
        with psycopg.connect(get_settings().postgres_dsn, connect_timeout=3):
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _reachable(), reason="PostgreSQL tak terjangkau")

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


@pytest.fixture
def client():
    from aegis.main import app

    with TestClient(app) as c:
        yield c


def _service() -> str:
    slug = f"svc-{uuid.uuid4().hex[:12]}"
    register_service(slug, "E2E", "TelcoX", "https://cp.example/req", "secret")
    return slug


def _init(client, trx, svc) -> str:
    r = client.post("/v1/session/init", json={"trx_id": trx, "service": svc})
    assert r.status_code == 200, r.text
    return r.json()["session_token"]


def _billing(client, payload: dict):
    body = json.dumps(payload)
    ts = datetime.now(UTC).isoformat()
    sig = compute_signature(get_settings().billing_hmac_secret, ts, body)
    return client.post("/v1/callback/billing", content=body, headers={
        "X-Aegis-Timestamp": ts, "X-Aegis-Signature": sig, "Content-Type": "application/json",
    })


def test_allow_then_callback_links_to_decision(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "aegis.api.scoring.mint_weboptin_url",
        lambda *a, **k: MintResult("minted", redirect_url="https://telco/x?token=1", host="telco"),
    )
    svc = _service()
    trx = f"trx-{uuid.uuid4().hex[:12]}"

    # 1) init → score (human) → allow + redirect
    tok = _init(client, trx, svc)
    r = client.post("/v1/score", json={
        "trx_id": trx, "service": svc, "session_token": tok,
        "schema_version": "1.0", "source": "facebook", "pub_id": "123", "signals": _HUMAN,
    })
    assert r.status_code == 200 and r.json()["decision"] == "allow"

    # 2) billing subscription callback untuk trx SAMA → tersambung ke keputusan (BUKAN orphan)
    ok = _billing(client, {
        "event": "subscription", "trx_id": trx, "charging_status": "success",
        "charging_fail_reason": None, "service_id": "SVC-1", "msisdn_hash": "h",
        "event_time": datetime.now(UTC).isoformat(),
    })
    assert ok.status_code == 200

    with connection() as conn:
        assert decisions_repo.get_by_trx(conn, trx) is not None  # keputusan ada
        outs = outcomes_repo.list_by_trx(conn, trx)
    assert any(o["callback_type"] == "subscription" for o in outs)  # label tersambung

    # 3) complaint menyusul
    assert _billing(client, {
        "event": "complaint", "trx_id": trx, "event_time": datetime.now(UTC).isoformat(),
    }).status_code == 200
    with connection() as conn:
        kinds = {o["callback_type"] for o in outcomes_repo.list_by_trx(conn, trx)}
    assert kinds == {"subscription", "complaint"}


def test_block_flow(client) -> None:
    svc = _service()
    trx = f"trx-{uuid.uuid4().hex[:12]}"
    tok = _init(client, trx, svc)
    r = client.post("/v1/score", json={
        "trx_id": trx, "service": svc, "session_token": tok,
        "schema_version": "1.0", "signals": _BOT,
    })
    assert r.status_code == 200 and r.json()["decision"] == "block"
