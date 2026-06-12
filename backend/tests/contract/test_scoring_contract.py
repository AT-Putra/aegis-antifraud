"""Contract `03 §3`: bentuk response session/init & score (provider scoring ↔ pre-landing)."""

import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from aegis.config import get_settings
from aegis.cp.client import MintResult
from aegis.registry.campaign import register_campaign
from aegis.registry.service import register_service


def _reachable() -> bool:
    try:
        with psycopg.connect(get_settings().postgres_dsn, connect_timeout=3):
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _reachable(), reason="PostgreSQL tak terjangkau")

_ORIGIN = "https://allowed.example"

_HUMAN = {
    "fingerprint": {"canvas_hash": "c1", "browser_environment": {"is_webview": False}},
    "behavior": {"mouse": {"move_count": 120}, "timing": {"interaction_count": 8}},
    "automation_hints": {"webdriver": False},
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


def _svc() -> str:
    slug = f"svc-{uuid.uuid4().hex[:12]}"
    register_service(slug, "C", "T", "https://cp.example/req", "secret")
    return slug


def _camp(svc: str) -> str:
    slug = f"camp-{uuid.uuid4().hex[:12]}"
    register_campaign(slug, "C", svc, [_ORIGIN])
    return slug


def _init(client, trx, svc, camp) -> str:
    r = client.post(
        "/v1/session/init", json={"trx_id": trx, "service": svc, "campaign": camp},
        headers={"Origin": _ORIGIN},
    )
    return r.json()["session_token"]


def test_session_init_shape(client) -> None:
    svc = _svc()
    camp = _camp(svc)
    body = client.post(
        "/v1/session/init", json={"trx_id": "x1", "service": svc, "campaign": camp},
        headers={"Origin": _ORIGIN},
    ).json()
    assert set(body) == {"session_token", "expires_at"}


def test_service_not_found_code(client) -> None:
    r = client.post(
        "/v1/session/init", json={"trx_id": "x2", "service": "nope-xyz", "campaign": "c"}
    )
    assert r.status_code == 404 and r.json()["code"] == "service_not_found"


def test_allow_shape(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "aegis.api.scoring.mint_weboptin_url",
        lambda *a, **k: MintResult("minted", redirect_url="https://t/x?token=1", host="t"),
    )
    svc = _svc()
    camp = _camp(svc)
    trx = f"trx-{uuid.uuid4().hex[:12]}"
    tok = _init(client, trx, svc, camp)
    body = client.post("/v1/score", headers={"Origin": _ORIGIN}, json={
        "trx_id": trx, "service": svc, "campaign": camp, "session_token": tok,
        "schema_version": "1.0", "signals": _HUMAN,
    }).json()
    assert body["decision"] == "allow" and set(body) == {"decision", "redirect_url"}


def test_block_shape_no_score(client) -> None:
    svc = _svc()
    camp = _camp(svc)
    trx = f"trx-{uuid.uuid4().hex[:12]}"
    tok = _init(client, trx, svc, camp)
    body = client.post("/v1/score", headers={"Origin": _ORIGIN}, json={
        "trx_id": trx, "service": svc, "campaign": camp, "session_token": tok,
        "schema_version": "1.0", "signals": _BOT,
    }).json()
    assert body["decision"] == "block"
    assert "final_score" not in body and set(body) == {"decision", "notice"}


def test_weboptin_unavailable_code(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "aegis.api.scoring.mint_weboptin_url",
        lambda *a, **k: MintResult("failed", reason="cp_error"),
    )
    svc = _svc()
    camp = _camp(svc)
    trx = f"trx-{uuid.uuid4().hex[:12]}"
    tok = _init(client, trx, svc, camp)
    r = client.post("/v1/score", headers={"Origin": _ORIGIN}, json={
        "trx_id": trx, "service": svc, "campaign": camp, "session_token": tok,
        "schema_version": "1.0", "signals": _HUMAN,
    })
    assert r.status_code == 502 and r.json()["code"] == "weboptin_unavailable"
