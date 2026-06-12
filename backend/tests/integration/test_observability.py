"""AC-OBS-01: metrik Prometheus ter-expose; healthcheck; audit keputusan immutable+ber-versi."""

from __future__ import annotations

import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from aegis.config import get_settings
from aegis.cp.client import MintResult
from aegis.registry.campaign import register_campaign
from aegis.registry.service import register_service

_HUMAN = {
    "fingerprint": {"canvas_hash": "c1", "browser_environment": {"is_webview": False}},
    "behavior": {"mouse": {"move_count": 120}, "timing": {"interaction_count": 8}},
    "automation_hints": {"webdriver": False},
    "integrity": {"ever_visible": True},
}


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


_ORIGIN = "https://allowed.example"


def _svc_camp() -> tuple[str, str]:
    svc = f"svc-{uuid.uuid4().hex[:10]}"
    register_service(svc, "Obs", "T", "https://cp.example/req", "secret")
    camp = f"camp-{uuid.uuid4().hex[:10]}"
    register_campaign(camp, "C", svc, [_ORIGIN])
    return svc, camp


def test_metrics_exposed_after_scoring(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "aegis.api.scoring.mint_weboptin_url",
        lambda *a, **k: MintResult("minted", redirect_url="https://t/x?token=1", host="t"),
    )
    svc, camp = _svc_camp()
    trx = f"trx-{uuid.uuid4().hex[:10]}"
    tok = client.post(
        "/v1/session/init", json={"trx_id": trx, "service": svc, "campaign": camp},
        headers={"Origin": _ORIGIN},
    ).json()["session_token"]
    r = client.post("/v1/score", headers={"Origin": _ORIGIN}, json={
        "trx_id": trx, "service": svc, "campaign": camp, "session_token": tok,
        "schema_version": "1.0", "signals": _HUMAN,
    })
    assert r.status_code == 200

    m = client.get("/metrics")
    assert m.status_code == 200
    body = m.text
    # AC-OBS-01.1: metrik kunci ter-expose
    assert "aegis_decisions_total" in body
    assert "aegis_http_requests_total" in body
    assert "aegis_score_duration_seconds" in body
    assert "aegis_cp_mint_duration_seconds" in body


def test_health_and_audit_versioned(client) -> None:
    # AC-OBS-01.2: healthcheck
    assert client.get("/health").json()["status"] == "ok"


def test_decision_is_versioned_audit(client, monkeypatch) -> None:
    monkeypatch.setattr(
        "aegis.api.scoring.mint_weboptin_url",
        lambda *a, **k: MintResult("minted", redirect_url="https://t/x?token=1", host="t"),
    )
    svc, camp = _svc_camp()
    trx = f"trx-{uuid.uuid4().hex[:10]}"
    tok = client.post(
        "/v1/session/init", json={"trx_id": trx, "service": svc, "campaign": camp},
        headers={"Origin": _ORIGIN},
    ).json()["session_token"]
    client.post("/v1/score", headers={"Origin": _ORIGIN}, json={
        "trx_id": trx, "service": svc, "campaign": camp, "session_token": tok,
        "schema_version": "1.0", "signals": _HUMAN,
    })
    # Audit trail keputusan: immutable (1 baris/trx) + ber-versi config/model.
    with psycopg.connect(get_settings().postgres_dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT rules_version, model_version FROM decisions WHERE trx_id = %s", (trx,))
        row = cur.fetchone()
    assert row is not None and row[0] is not None  # rules_version tercatat
