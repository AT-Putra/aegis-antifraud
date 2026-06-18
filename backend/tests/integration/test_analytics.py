"""AC-ANALYTICS-01/02: atribusi berjenjang, konversi timezone, bentuk kontrak (03 §7).

Insert baris uji **sinkron** (default clickhouse_connect, TANPA async_insert) supaya
langsung queryable — JANGAN pakai async_insert di test (bikin flaky). Di-skip bila DB
tak terjangkau. Auth: mint JWT langsung (login endpoint baru ada di T-15).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import clickhouse_connect
import psycopg
import pytest
from _authkit import auth_headers
from fastapi.testclient import TestClient

from aegis.config import get_settings
from aegis.db.migrate import migrate_olap, migrate_oltp

_TRAFFIC_COLS = [
    "trx_id", "device_id", "service", "source", "pub_id", "signals", "features",
    "ip_country", "ip_asn", "ip_isp", "connection_type", "vpn_proxy_tor", "ip_reputation",
    "decision", "final_score", "weboptin_status", "browser", "os", "device_type",
    "device_brand", "device_model", "is_webview", "score_breakdown", "ts",
]
_DLOG_COLS = [
    "trx_id", "device_id", "service", "source", "pub_id", "final_score", "decision",
    "weboptin_status", "rules_version", "model_version", "ts",
]


def _both_reachable(s) -> object | None:
    try:
        with psycopg.connect(s.postgres_dsn, connect_timeout=3):
            pass
        return clickhouse_connect.get_client(
            host=s.clickhouse_host, port=s.clickhouse_port, username=s.clickhouse_user,
            password=s.clickhouse_password, database=s.clickhouse_db, connect_timeout=3,
        )
    except Exception:
        return None


@pytest.fixture(scope="module")
def ch():
    s = get_settings()
    client = _both_reachable(s)
    if client is None:
        pytest.skip("PostgreSQL/ClickHouse tak terjangkau")
    migrate_oltp(s)
    migrate_olap(s)
    return client


@pytest.fixture
def client():
    from aegis.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth() -> dict:
    return auth_headers("tester", "admin")


def _traffic_row(*, trx, service, source, pub_id, decision, ts, **kw) -> list:
    return [
        trx, kw.get("device_id", "dev-x"), service, source, pub_id,
        json.dumps(kw.get("signals", {"fingerprint": {"canvas_hash": "c1"}})),
        json.dumps(kw.get("features", {"automation_score": 0.1})),
        kw.get("country", "ID"), kw.get("asn", 12345), kw.get("isp", "ISP"),
        kw.get("connection_type", "mobile"), kw.get("vpn", 0), kw.get("rep", "clean"),
        decision, kw.get("final_score", 0.2), kw.get("weboptin_status", "minted"),
        kw.get("browser", "Chrome"), kw.get("os", "Android"), kw.get("device_type", "mobile"),
        kw.get("brand", "Samsung"), kw.get("model", "SM-S921B"), kw.get("is_webview", 0),
        json.dumps(kw.get("breakdown", {"rules": 0.1, "isolation_forest": 0.2, "lightgbm": 0.3})),
        ts,
    ]


def test_berjenjang_attribution(ch, client, auth) -> None:
    """Filter pub_id di-scope (service,source): svcA & svcB sama-sama pub '1', terpisah."""
    svc_a, svc_b = f"ana-a-{uuid.uuid4().hex[:8]}", f"ana-b-{uuid.uuid4().hex[:8]}"
    ts = datetime(2030, 3, 1, 6, 0, 0)
    rows = [
        _traffic_row(trx=f"t-{uuid.uuid4().hex[:8]}", service=svc_a, source="fb",
                     pub_id="1", decision="allow", ts=ts) for _ in range(2)
    ] + [
        _traffic_row(trx=f"t-{uuid.uuid4().hex[:8]}", service=svc_b, source="fb",
                     pub_id="1", decision="allow", ts=ts) for _ in range(3)
    ]
    ch.insert("traffic_events", rows, column_names=_TRAFFIC_COLS)

    q = {"from": "2030-03-01T00:00:00", "to": "2030-03-02T00:00:00", "dimension": "pub_id"}
    a = client.get("/v1/analytics/breakdown", params={**q, "service": svc_a, "source": "fb"},
                   headers=auth).json()
    b = client.get("/v1/analytics/breakdown", params={**q, "service": svc_b, "source": "fb"},
                   headers=auth).json()
    assert a == [{"key": "1", "count": 2}]
    assert b == [{"key": "1", "count": 3}]


def test_summary_and_search_shape(ch, client, auth) -> None:
    svc = f"ana-s-{uuid.uuid4().hex[:8]}"
    ts = datetime(2030, 4, 1, 6, 0, 0)
    trx_allow = f"t-{uuid.uuid4().hex[:8]}"
    trx_block = f"t-{uuid.uuid4().hex[:8]}"
    ch.insert("traffic_events", [
        _traffic_row(trx=trx_allow, service=svc, source="fb", pub_id="1",
                     decision="allow", ts=ts),
        _traffic_row(trx=trx_block, service=svc, source="fb", pub_id="1",
                     decision="block", ts=ts, weboptin_status="na"),
    ], column_names=_TRAFFIC_COLS)
    q = {"from": "2030-04-01T00:00:00", "to": "2030-04-02T00:00:00", "service": svc}

    s = client.get("/v1/analytics/summary", params=q, headers=auth).json()
    assert s["total"] == 2 and s["allow"] == 1 and s["block"] == 1
    # fraud_est = Opsi B (allow + sinyal fraud terkonfirmasi via OLAP mirror); tak ada outcome → 0
    assert s["fraud_est"] == 0 and s["complaints"] == 0
    assert set(s) == {"total", "allow", "block", "weboptin_failed", "fraud_est",
                      "complaints", "charging_fail_breakdown"}

    res = client.get("/v1/analytics/search", params=q, headers=auth).json()
    assert {r["trx_id"] for r in res} == {trx_allow, trx_block}
    assert set(res[0]) >= {"trx_id", "decision", "service", "ts"}


def test_timeseries_timezone_bucket(ch, client, auth) -> None:
    """ts 2030-05-01 18:30 UTC → WIB 2030-05-02 → bucket harian harus 02 Mei (K2)."""
    svc = f"ana-tz-{uuid.uuid4().hex[:8]}"
    ch.insert("traffic_events", [
        _traffic_row(trx=f"t-{uuid.uuid4().hex[:8]}", service=svc, source="fb",
                     pub_id="1", decision="allow", ts=datetime(2030, 5, 1, 18, 30, 0)),
    ], column_names=_TRAFFIC_COLS)
    pts = client.get("/v1/analytics/timeseries", headers=auth, params={
        "metric": "total", "granularity": "day", "tz": "Asia/Jakarta", "service": svc,
        "from": "2030-05-01T00:00:00", "to": "2030-05-03T00:00:00",
    }).json()
    assert len(pts) == 1 and pts[0]["value"] == 1.0
    assert pts[0]["bucket_ts"].startswith("2030-05-02")


def test_decision_detail(ch, client, auth) -> None:
    svc = f"ana-d-{uuid.uuid4().hex[:8]}"
    trx = f"t-{uuid.uuid4().hex[:8]}"
    ch.insert("traffic_events", [
        _traffic_row(trx=trx, service=svc, source="fb", pub_id="1", decision="block",
                     ts=datetime(2030, 6, 1, 6, 0, 0), weboptin_status="na"),
    ], column_names=_TRAFFIC_COLS)
    d = client.get(f"/v1/analytics/decision/{trx}", headers=auth).json()
    assert d["trx_id"] == trx and d["decision"] == "block"
    assert set(d["score_breakdown"]) == {"rules", "isolation_forest", "lightgbm"}
    assert "is_webview" in d["device_info"] and "country" in d["ip_intelligence"]


def test_decision_detail_ip_address(ch, client, auth) -> None:
    # T-23 audit: raw IP tersimpan di traffic_events → muncul di ip_intelligence detail.
    trx = f"t-{uuid.uuid4().hex[:8]}"
    ch.insert(
        "traffic_events",
        [[trx, "block", "203.0.113.9"]],
        column_names=["trx_id", "decision", "ip_address"],
    )
    d = client.get(f"/v1/analytics/decision/{trx}", headers=auth).json()
    assert d["ip_intelligence"]["ip_address"] == "203.0.113.9"


def test_decision_detail_404(ch, client, auth) -> None:
    r = client.get(f"/v1/analytics/decision/nope-{uuid.uuid4().hex[:8]}", headers=auth)
    assert r.status_code == 404


def _seed_oltp_decision(trx: str, *, decision: str, reason: str | None,
                        rules_version: int = 1, threshold: float = 0.5) -> None:
    """Sisipkan baris OLTP `decisions` (sumber rules_version/threshold/reason di detail).

    FK device_id/service_id dibiarkan NULL (nullable) → tak perlu seed device/service.
    """
    s = get_settings()
    with psycopg.connect(s.postgres_dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO decisions (trx_id, decision, threshold_used, rules_version, reason, "
            "weboptin_status) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (trx_id) DO NOTHING",
            (trx, decision, threshold, rules_version, reason,
             "na" if decision == "block" else "minted"),
        )
        conn.commit()


def test_decision_detail_explainability_stored_features(ch, client, auth) -> None:
    """Fitur tersimpan → explainability.available, feature_source=stored_features, faktor benar."""
    svc = f"ana-x-{uuid.uuid4().hex[:8]}"
    trx = f"t-{uuid.uuid4().hex[:8]}"
    # automation_score=1.0 (×0.2) + webview_risk=1.0 (×0.3) = rules 0.5
    feats = {"automation_score": 1.0, "webview_risk": 1.0}
    ch.insert("traffic_events", [
        _traffic_row(trx=trx, service=svc, source="fb", pub_id="1", decision="block",
                     ts=datetime(2030, 6, 2, 6, 0, 0), weboptin_status="na",
                     features=feats, final_score=0.5,
                     breakdown={"rules": 0.5, "isolation_forest": None, "lightgbm": None}),
    ], column_names=_TRAFFIC_COLS)
    _seed_oltp_decision(trx, decision="block", reason=None, rules_version=1, threshold=0.5)

    d = client.get(f"/v1/analytics/decision/{trx}", headers=auth).json()
    ex = d["explainability"]
    assert ex["available"] is True
    assert ex["feature_source"] == "stored_features"
    assert ex["rules_version_used"] == 1
    contrib = {f["name"]: f["contribution"] for f in ex["rules"]["factors"]}
    assert contrib["automation_score"] == 0.2
    assert contrib["webview_risk"] == 0.3
    assert ex["rules"]["soft_score"] == 0.5
    assert ex["models"]["attribution_available"] is False


def test_decision_detail_explainability_recomputed(ch, client, auth) -> None:
    """OLAP features kosong + signals valid → recomputed_from_signals + warnings."""
    svc = f"ana-rc-{uuid.uuid4().hex[:8]}"
    trx = f"t-{uuid.uuid4().hex[:8]}"
    signals = {"fingerprint": {"canvas_hash": "c1", "browser_environment": {"is_webview": False}},
               "behavior": {"mouse": {"move_count": 0}}, "automation_hints": {"webdriver": False}}
    ch.insert("traffic_events", [
        _traffic_row(trx=trx, service=svc, source="fb", pub_id="1", decision="allow",
                     ts=datetime(2030, 6, 3, 6, 0, 0), signals=signals, features={},
                     breakdown={"rules": 0.2, "isolation_forest": None, "lightgbm": None}),
    ], column_names=_TRAFFIC_COLS)
    _seed_oltp_decision(trx, decision="allow", reason=None, rules_version=1, threshold=0.5)

    d = client.get(f"/v1/analytics/decision/{trx}", headers=auth).json()
    ex = d["explainability"]
    assert ex["available"] is True
    assert ex["feature_source"] == "recomputed_from_signals"
    assert ex["warnings"]  # ada peringatan rekonstruksi terdegradasi


def test_decision_detail_explainability_degraded_no_oltp(ch, client, auth) -> None:
    """Tanpa baris OLTP (rules_version tak diketahui) → available:false, tetap 200 (bukan 500)."""
    svc = f"ana-dg-{uuid.uuid4().hex[:8]}"
    trx = f"t-{uuid.uuid4().hex[:8]}"
    ch.insert("traffic_events", [
        _traffic_row(trx=trx, service=svc, source="fb", pub_id="1", decision="block",
                     ts=datetime(2030, 6, 4, 6, 0, 0), weboptin_status="na"),
    ], column_names=_TRAFFIC_COLS)
    r = client.get(f"/v1/analytics/decision/{trx}", headers=auth)
    assert r.status_code == 200
    assert r.json()["explainability"]["available"] is False


def test_stream_emits_event(ch, client, auth) -> None:
    svc = f"ana-st-{uuid.uuid4().hex[:8]}"
    trx = f"t-{uuid.uuid4().hex[:8]}"
    camp = f"camp-{uuid.uuid4().hex[:8]}"
    # Sertakan campaign & reason (kolom feed F-08) untuk verifikasi ikut terkirim di SSE.
    # ts jauh ke depan (2099) → baris ini dijamin masuk feed "terbaru" (LIMIT 20) walau
    # test lain menyemai decision_log bertanggal lebih awal (isolasi pada dev DB bersama).
    sb = '{"rules": 0.5, "isolation_forest": 0.3, "lightgbm": 0.7}'
    ch.insert("decision_log", [[
        trx, "dev-x", svc, "fb", "1", 0.9, "block", "na", 1, 0,
        datetime(2099, 1, 1, 6, 0, 0), camp, "rule:webdriver", sb,
    ]], column_names=[*_DLOG_COLS, "campaign", "reason", "score_breakdown"])
    r = client.get("/v1/stream", params={"limit": 1}, headers=auth)
    assert r.status_code == 200
    assert "event: kpi" in r.text
    # Feed decision membawa campaign (bug sebelumnya: kosong) + reason + score_breakdown.
    assert camp in r.text
    assert "rule:webdriver" in r.text
    assert "isolation_forest" in r.text
    assert "lightgbm" in r.text


def test_requires_auth(ch, client) -> None:
    # HTTPBearer(auto_error) → 401 saat Authorization header tak ada.
    assert client.get("/v1/analytics/summary").status_code == 401


def test_timeseries_bad_metric(ch, client, auth) -> None:
    r = client.get("/v1/analytics/timeseries", params={"metric": "bogus"}, headers=auth)
    assert r.status_code == 400
