"""AC-CAMPAIGN-01..03 (F-16, T-21): registry+validasi, CORS per-campaign, atribusi+fraud_est.

Di-skip bila PostgreSQL tak terjangkau. Insert OLAP sinkron (tanpa async_insert).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

from aegis.config import get_settings
from aegis.cp.client import MintResult
from aegis.db.migrate import migrate_oltp
from aegis.db.oltp import users_repo
from aegis.db.postgres import connection
from aegis.registry.service import register_service
from aegis.security.hmac_auth import compute_signature
from aegis.security.jwt_auth import create_token
from aegis.security.passwords import hash_password

_ORIGIN = "https://allowed.example"

_HUMAN = {
    "fingerprint": {"canvas_hash": "c1", "webgl": {"renderer": "Mali"},
                    "browser_environment": {"is_webview": False}},
    "behavior": {"mouse": {"move_count": 120, "velocity_mean": 1.2},
                 "touch": {"tap_count": 3}, "timing": {"interaction_count": 8}},
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


@pytest.fixture(scope="module", autouse=True)
def _migrated():
    migrate_oltp(get_settings())  # campaign pakai OLTP saja (fraud_est, CRUD, CORS)


@pytest.fixture
def client():
    from aegis.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth() -> dict:
    username = f"adm-{uuid.uuid4().hex[:10]}"
    with connection() as conn:
        users_repo.insert_user(
            conn, username=username, password_hash=hash_password("x"), role="admin"
        )
    return {"Authorization": f"Bearer {create_token(username, 'admin')}"}


def _service() -> str:
    slug = f"svc-{uuid.uuid4().hex[:10]}"
    register_service(slug, "Svc", "Telco", "https://cp.example/req", "secret")
    return slug


def _create_campaign(client, auth, service, origins=None) -> tuple[str, str]:
    slug = f"camp-{uuid.uuid4().hex[:10]}"
    r = client.post("/v1/admin/campaigns", headers=auth, json={
        "slug": slug, "name": "Camp", "service": service, "allowed_origins": origins or [],
    })
    assert r.status_code == 200, r.text
    return slug, r.json()["id"]


# --- AC-CAMPAIGN-01: registry & validasi ---
def test_campaign_crud_and_validation(client, auth) -> None:
    svc = _service()
    slug, cid = _create_campaign(client, auth, svc, ["https://ext.example"])

    listing = client.get("/v1/admin/campaigns", headers=auth, params={"service": svc}).json()
    item = next(c for c in listing if c["id"] == cid)
    assert item["slug"] == slug and item["service"] == svc
    assert item["allowed_origins"] == ["https://ext.example"]

    # slug duplikat → 409
    dup = client.post("/v1/admin/campaigns", headers=auth, json={
        "slug": slug, "name": "X", "service": svc, "allowed_origins": [],
    })
    assert dup.status_code == 409

    # service tak dikenal → 404
    bad = client.post("/v1/admin/campaigns", headers=auth, json={
        "slug": f"c-{uuid.uuid4().hex[:8]}", "name": "X", "service": "nope-xyz",
        "allowed_origins": [],
    })
    assert bad.status_code == 404

    # nonaktifkan → session/init tolak
    client.put(f"/v1/admin/campaigns/{cid}", headers=auth, json={"status": "inactive"})
    r = client.post("/v1/session/init", json={
        "trx_id": "t-x", "service": svc, "campaign": slug,
    })
    assert r.status_code == 404 and r.json()["code"] == "campaign_not_found"


def test_campaign_required_and_belongs_to_service(client, auth) -> None:
    svc1 = _service()
    svc2 = _service()
    slug, _ = _create_campaign(client, auth, svc1)

    # campaign wajib (pydantic) → 422
    assert client.post(
        "/v1/session/init", json={"trx_id": "t1", "service": svc1}
    ).status_code == 422

    # campaign milik svc1 dipakai dgn svc2 → 404
    r = client.post("/v1/session/init", json={
        "trx_id": "t2", "service": svc2, "campaign": slug,
    })
    assert r.status_code == 404 and r.json()["code"] == "campaign_not_found"


# --- AC-CAMPAIGN-02: CORS per-campaign ---
def test_campaign_cors(client, auth) -> None:
    svc = _service()
    slug, _ = _create_campaign(client, auth, svc, ["https://allowed.example"])
    body = {"trx_id": f"t-{uuid.uuid4().hex[:8]}", "service": svc, "campaign": slug}

    ok = client.post("/v1/session/init", json=body, headers={"Origin": _ORIGIN})
    assert ok.status_code == 200, ok.text

    missing = client.post("/v1/session/init", json=body)
    assert missing.status_code == 403 and missing.json()["code"] == "forbidden_origin"

    bad = client.post("/v1/session/init", json=body, headers={"Origin": "https://evil.example"})
    assert bad.status_code == 403 and bad.json()["code"] == "forbidden_origin"

    tok = ok.json()["session_token"]
    score_body = {
        "trx_id": body["trx_id"], "service": svc, "campaign": slug, "session_token": tok,
        "schema_version": "1.0", "source": "fb", "pub_id": "1", "signals": _HUMAN,
    }
    score_missing = client.post("/v1/score", json=score_body)
    assert score_missing.status_code == 403 and score_missing.json()["code"] == "forbidden_origin"


# --- AC-CAMPAIGN-03: atribusi & fraud_est (Opsi B, berjenjang) ---
def _billing(client, payload: dict):
    body = json.dumps(payload)
    ts = datetime.now(UTC).isoformat()
    sig = compute_signature(get_settings().billing_hmac_secret, ts, body)
    return client.post("/v1/callback/billing", content=body, headers={
        "X-Aegis-Timestamp": ts, "X-Aegis-Signature": sig, "Content-Type": "application/json",
    })


def test_campaign_attribution_fraud_est(client, auth, monkeypatch) -> None:
    monkeypatch.setattr(
        "aegis.api.scoring.mint_weboptin_url",
        lambda *a, **k: MintResult("minted", redirect_url="https://t/x?token=1", host="t"),
    )
    svc = _service()
    slug, _ = _create_campaign(client, auth, svc, [_ORIGIN])
    other, _ = _create_campaign(client, auth, svc, [_ORIGIN])
    trx = f"trx-{uuid.uuid4().hex[:10]}"

    tok = client.post("/v1/session/init", headers={"Origin": _ORIGIN}, json={
        "trx_id": trx, "service": svc, "campaign": slug,
    }).json()["session_token"]
    r = client.post("/v1/score", headers={"Origin": _ORIGIN}, json={
        "trx_id": trx, "service": svc, "campaign": slug, "session_token": tok,
        "schema_version": "1.0", "source": "fb", "pub_id": "1", "signals": _HUMAN,
    })
    assert r.status_code == 200 and r.json()["decision"] == "allow"

    # sinyal fraud: komplain → fraud_est Opsi B menghitung trx allow ini
    assert _billing(client, {
        "event": "complaint", "trx_id": trx, "event_time": datetime.now(UTC).isoformat(),
    }).status_code == 200

    # fraud_est/complaints kini full-OLAP (ADR-014): traffic_events (skor) & outcome_log
    # (mirror callback) ditulis async_insert → flush queue agar deterministik di test.
    import clickhouse_connect

    _s = get_settings()
    _ch = clickhouse_connect.get_client(
        host=_s.clickhouse_host, port=_s.clickhouse_port, username=_s.clickhouse_user,
        password=_s.clickhouse_password, database=_s.clickhouse_db,
    )
    _ch.command("SYSTEM FLUSH ASYNC INSERT QUEUE")

    win = {
        "from": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        "to": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
    }
    s = client.get("/v1/analytics/summary", headers=auth,
                   params={**win, "campaign": slug}).json()
    assert s["fraud_est"] == 1 and s["complaints"] == 1

    # scoping berjenjang: campaign lain tak terhitung
    s2 = client.get("/v1/analytics/summary", headers=auth,
                    params={**win, "campaign": other}).json()
    assert s2["fraud_est"] == 0
