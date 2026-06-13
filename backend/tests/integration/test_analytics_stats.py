"""Statistik analitik tambahan (03 §7): top-N alasan blok + rata-rata metrik behavior.

block-reasons → OLTP `decisions.reason` (sumber kebenaran). behavior-stats → OLAP
`traffic_events.features` (flattened, skew-free). Di-skip bila DB tak terjangkau.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import clickhouse_connect
import psycopg
import pytest
from fastapi.testclient import TestClient

from aegis.config import get_settings
from aegis.db.migrate import migrate_olap, migrate_oltp
from aegis.db.oltp import decisions_repo
from aegis.db.postgres import connection
from aegis.security.jwt_auth import create_token

_TRAFFIC_COLS = [
    "trx_id", "device_id", "service", "source", "pub_id", "signals", "features",
    "ip_country", "ip_asn", "ip_isp", "connection_type", "vpn_proxy_tor", "ip_reputation",
    "decision", "final_score", "weboptin_status", "browser", "os", "device_type",
    "device_brand", "device_model", "is_webview", "score_breakdown", "ts",
]


def _ch():
    s = get_settings()
    try:
        c = clickhouse_connect.get_client(
            host=s.clickhouse_host, port=s.clickhouse_port, username=s.clickhouse_user,
            password=s.clickhouse_password, database=s.clickhouse_db,
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
    return {"Authorization": f"Bearer {create_token('tester', 'admin')}"}


def _features(**kw) -> dict:
    base = {
        "mouse_velocity_mean": 1.0, "mouse_direction_changes": 2.0, "scroll_depth_pct": 50.0,
        "tap_count": 3.0, "interaction_count": 6.0, "time_to_cta_ms": 4000.0,
    }
    base.update(kw)
    return base


def _traffic_row(*, trx, service, decision, ts, features) -> list:
    return [
        trx, "dev-x", service, "fb", "1",
        json.dumps({"behavior": {"mouse": {}}}), json.dumps(features),
        "ID", 12345, "ISP", "mobile", 0, "clean",
        decision, 0.2, "minted", "Chrome", "Android", "mobile", "Samsung", "SM", 0,
        json.dumps({"rules": 0.1}), ts,
    ]


def test_behavior_stats_average(client, auth) -> None:
    ch = _ch()
    if ch is None:
        pytest.skip("ClickHouse tak terjangkau")
    svc = f"beh-{uuid.uuid4().hex[:8]}"
    ts = datetime(2031, 1, 1, 6, 0, 0)
    # dua baris: velocity 2 & 4 → rata-rata 3.
    ch.insert("traffic_events", [
        _traffic_row(trx=f"t-{uuid.uuid4().hex[:8]}", service=svc, decision="allow", ts=ts,
                     features=_features(mouse_velocity_mean=2.0)),
        _traffic_row(trx=f"t-{uuid.uuid4().hex[:8]}", service=svc, decision="allow", ts=ts,
                     features=_features(mouse_velocity_mean=4.0)),
    ], column_names=_TRAFFIC_COLS)

    q = {"from": "2031-01-01T00:00:00", "to": "2031-01-02T00:00:00", "service": svc}
    rows = client.get("/v1/analytics/behavior-stats", params=q, headers=auth).json()
    by = {r["metric"]: r for r in rows}
    assert by["mouse_velocity_mean"]["avg"] == 3.0
    assert by["mouse_velocity_mean"]["sample"] == 2
    # semua metrik behavior hadir & berlabel.
    for k in ("scroll_depth_pct", "tap_count", "interaction_count", "time_to_cta_ms"):
        assert k in by and by[k]["label"]


def test_block_reasons_top_n(client, auth) -> None:
    svc_slug = f"br-{uuid.uuid4().hex[:8]}"
    # daftarkan service agar scoping (opsional) valid; di sini uji unscoped.
    with connection() as conn:
        # 2x rule:webdriver, 1x threshold (reason NULL) → urut desc.
        for reason in ("rule:webdriver", "rule:webdriver", None):
            decisions_repo.insert_decision(
                conn, trx_id=f"{svc_slug}-{uuid.uuid4().hex[:8]}", device_id=None,
                service_id=None, source="fb", pub_id="1", final_score=0.9, decision="block",
                threshold_used=0.5, rules_version=None, model_version=None, reason=reason,
                weboptin_status="na",
            )
        conn.commit()

    rows = client.get("/v1/analytics/block-reasons", params={"limit": 10}, headers=auth).json()
    by = {r["reason"]: r["count"] for r in rows}
    assert by.get("rule:webdriver", 0) >= 2
    assert by.get("threshold", 0) >= 1  # reason NULL dikelompokkan 'threshold'
    # terurut menurun.
    counts = [r["count"] for r in rows]
    assert counts == sorted(counts, reverse=True)


def test_stats_accessible_to_user(client) -> None:
    user = {"Authorization": f"Bearer {create_token('u', 'user')}"}
    assert client.get("/v1/analytics/block-reasons", headers=user).status_code == 200
    assert client.get("/v1/analytics/behavior-stats", headers=user).status_code == 200
