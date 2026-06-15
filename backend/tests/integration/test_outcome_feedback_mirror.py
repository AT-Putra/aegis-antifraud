"""Mirror outcomes/feedback → OLAP + agregat full-OLAP (ADR-014).

Verifikasi: (1) write-path callback & feedback-review mengisi outcome_log/feedback_log;
(2) summary.fraud_est / complaints / charging_fail_breakdown & search?charging_status
dihitung dari OLAP. Di-skip bila DB tak terjangkau.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import clickhouse_connect
import psycopg
import pytest
from _authkit import auth_headers
from fastapi.testclient import TestClient

from aegis.config import get_settings
from aegis.db.migrate import migrate_olap, migrate_oltp
from aegis.security.hmac_auth import compute_signature

_TRAFFIC_COLS = [
    "trx_id", "device_id", "service", "source", "pub_id", "signals", "features",
    "ip_country", "ip_asn", "ip_isp", "connection_type", "vpn_proxy_tor", "ip_reputation",
    "decision", "final_score", "weboptin_status", "browser", "os", "device_type",
    "device_brand", "device_model", "is_webview", "score_breakdown", "ts", "campaign",
]


def _ch():
    s = get_settings()
    try:
        c = clickhouse_connect.get_client(
            host=s.clickhouse_host, port=s.clickhouse_port, username=s.clickhouse_user,
            password=s.clickhouse_password, database=s.clickhouse_db, connect_timeout=3,
        )
        c.query("SELECT 1")
        return c
    except Exception:
        return None


def _pg_ok() -> bool:
    try:
        with psycopg.connect(get_settings().postgres_dsn, connect_timeout=3):
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _pg_ok(), reason="PostgreSQL tak terjangkau")


@pytest.fixture(scope="module", autouse=True)
def _migrated():
    migrate_oltp(get_settings())
    if _ch() is not None:
        migrate_olap(get_settings())


@pytest.fixture
def client():
    from aegis.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth() -> dict:
    return auth_headers("tester", "admin")


def _signed(body: dict) -> tuple[str, dict]:
    raw = json.dumps(body)
    ts = datetime.now(UTC).isoformat()  # harus fresh (anti-replay window)
    sig = compute_signature(get_settings().billing_hmac_secret, ts, raw)
    return raw, {"x-aegis-timestamp": ts, "x-aegis-signature": sig,
                 "content-type": "application/json"}


def _traffic_row(*, trx, service, decision, ts, campaign="") -> list:
    return [
        trx, "dev-x", service, "fb", "1", json.dumps({}), json.dumps({"automation_score": 0.1}),
        "ID", 12345, "ISP", "mobile", 0, "clean", decision, 0.2, "minted", "Chrome", "Android",
        "mobile", "Samsung", "SM", 0, json.dumps({"rules": 0.1}), ts, campaign,
    ]


def test_callback_mirrors_to_olap(client) -> None:
    """POST /v1/callback/billing (complaint) → baris muncul di outcome_log OLAP."""
    ch = _ch()
    if ch is None:
        pytest.skip("ClickHouse tak terjangkau")
    trx = f"mir-{uuid.uuid4().hex[:10]}"
    raw, headers = _signed({
        "event": "complaint", "trx_id": trx, "event_time": datetime.now(UTC).isoformat(),
    })
    r = client.post("/v1/callback/billing", content=raw, headers=headers)
    assert r.status_code == 200, r.text
    # mirror dikirim async_insert (wait=0) → flush buffer server agar terlihat di test.
    ch.command("SYSTEM FLUSH ASYNC INSERT QUEUE")
    rows = ch.query(
        "SELECT callback_type FROM outcome_log WHERE trx_id = {t:String}",
        parameters={"t": trx},
    ).result_rows
    assert any(x[0] == "complaint" for x in rows)


def test_fraud_est_complaints_from_olap(client, auth) -> None:
    """fraud_est & complaints dihitung dari traffic_events + outcome_log (tanpa OLTP)."""
    ch = _ch()
    if ch is None:
        pytest.skip("ClickHouse tak terjangkau")
    svc = f"frd-{uuid.uuid4().hex[:8]}"
    ts = datetime(2032, 1, 1, 6, 0, 0)
    trx_fraud = f"{svc}-allow-cmpl"
    # 1 trx allow + komplain → fraud_est=1 & complaints=1; 1 trx allow tanpa sinyal.
    ch.insert("traffic_events", [
        _traffic_row(trx=trx_fraud, service=svc, decision="allow", ts=ts),
        _traffic_row(trx=f"{svc}-allow-clean", service=svc, decision="allow", ts=ts),
    ], column_names=_TRAFFIC_COLS)
    # insert mirror sinkron (test) → deterministik.
    ch.insert("outcome_log", [[trx_fraud, "complaint", "", "", ts]],
              column_names=["trx_id", "callback_type", "charging_status",
                            "charging_fail_reason", "received_at"])

    q = {"from": "2032-01-01T00:00:00", "to": "2032-01-02T00:00:00", "service": svc}
    s = client.get("/v1/analytics/summary", params=q, headers=auth).json()
    assert s["fraud_est"] == 1
    assert s["complaints"] == 1


def test_charging_breakdown_and_search_filter_from_olap(client, auth) -> None:
    """charging_fail_breakdown (summary) & search?charging_status dari outcome_log."""
    ch = _ch()
    if ch is None:
        pytest.skip("ClickHouse tak terjangkau")
    svc = f"chg-{uuid.uuid4().hex[:8]}"
    ts = datetime(2032, 2, 1, 6, 0, 0)
    trx = f"{svc}-failtrx"
    ch.insert("traffic_events", [
        _traffic_row(trx=trx, service=svc, decision="allow", ts=ts),
    ], column_names=_TRAFFIC_COLS)
    ch.insert("outcome_log", [[trx, "subscription", "failed", "daily_limit_reached", ts]],
              column_names=["trx_id", "callback_type", "charging_status",
                            "charging_fail_reason", "received_at"])

    q = {"from": "2032-02-01T00:00:00", "to": "2032-02-02T00:00:00", "service": svc}
    s = client.get("/v1/analytics/summary", params=q, headers=auth).json()
    assert s["charging_fail_breakdown"].get("daily_limit_reached") == 1

    res = client.get("/v1/analytics/search",
                     params={**q, "charging_status": "failed"}, headers=auth).json()
    assert any(row["trx_id"] == trx for row in res)


def test_feedback_review_mirrors_and_fraud_est(client, auth) -> None:
    """feedback accepted-robot → feedback_log → fraud_est menghitungnya."""
    ch = _ch()
    if ch is None:
        pytest.skip("ClickHouse tak terjangkau")
    svc = f"fb-{uuid.uuid4().hex[:8]}"
    ts = datetime(2032, 3, 1, 6, 0, 0)
    trx = f"{svc}-robot"
    ch.insert("traffic_events", [
        _traffic_row(trx=trx, service=svc, decision="allow", ts=ts),
    ], column_names=_TRAFFIC_COLS)
    # mirror feedback langsung sinkron (uji jalur agregat; review live diuji terpisah).
    ch.insert("feedback_log", [[str(uuid.uuid4()), trx, "robot", "accepted", ts, 1]],
              column_names=["id", "trx_id", "flagged_label", "review_status",
                            "created_at", "version"])

    q = {"from": "2032-03-01T00:00:00", "to": "2032-03-02T00:00:00", "service": svc}
    s = client.get("/v1/analytics/summary", params=q, headers=auth).json()
    assert s["fraud_est"] == 1
