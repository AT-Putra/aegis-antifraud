"""Contract `03 §4`: callback billing dua fase, idempotensi, signature, orphan."""

import json
import uuid
from datetime import UTC, datetime

import psycopg
import pytest
from fastapi.testclient import TestClient

from aegis.config import get_settings
from aegis.db.oltp import outcomes_repo
from aegis.db.postgres import connection
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


def _post(client, payload: dict, *, sig: str | None = None):
    body = json.dumps(payload)
    ts = datetime.now(UTC).isoformat()
    signature = sig if sig is not None else compute_signature(
        get_settings().billing_hmac_secret, ts, body
    )
    return client.post("/v1/callback/billing", content=body, headers={
        "X-Aegis-Timestamp": ts, "X-Aegis-Signature": signature, "Content-Type": "application/json",
    })


def _sub(trx: str) -> dict:
    return {
        "event": "subscription", "trx_id": trx, "charging_status": "failed",
        "charging_fail_reason": "daily_limit_reached", "service_id": "S",
        "msisdn_hash": "h", "event_time": datetime.now(UTC).isoformat(),
    }


def test_subscription_and_complaint_ok(client) -> None:
    trx = f"trx-{uuid.uuid4().hex[:12]}"
    assert _post(client, _sub(trx)).json() == {"status": "ok"}
    assert _post(client, {
        "event": "complaint", "trx_id": trx, "event_time": datetime.now(UTC).isoformat()
    }).json() == {"status": "ok"}


def test_invalid_signature_401(client) -> None:
    assert _post(client, _sub(f"trx-{uuid.uuid4().hex[:12]}"), sig="deadbeef").status_code == 401


def test_idempotent_single_row(client) -> None:
    trx = f"trx-{uuid.uuid4().hex[:12]}"
    assert _post(client, _sub(trx)).status_code == 200
    assert _post(client, _sub(trx)).status_code == 200  # idempoten
    with connection() as conn:
        rows = outcomes_repo.list_by_trx(conn, trx)
    subs = [o for o in rows if o["callback_type"] == "subscription"]
    assert len(subs) == 1  # tidak digandakan


def test_orphan_stored(client) -> None:
    trx = f"trx-{uuid.uuid4().hex[:12]}"  # tak ada decision → orphan
    assert _post(client, _sub(trx)).status_code == 200
    with connection() as conn:
        assert outcomes_repo.list_by_trx(conn, trx)  # tetap tersimpan
