"""AC-RETRAIN-01: pipeline retraining end-to-end + AC-RETRAIN-01.2 (model tak auto-aktif).

Seed dataset uji (decisions+outcomes OLTP + features OLAP) cukup utk melatih LGBM
(≥20/kelas), jalankan run_retrain, verifikasi model terdaftar active=false, artefak
tertulis, job done, lalu aktivasi (approval) berhasil. Di-skip bila DB tak terjangkau.

Insert OLAP **sinkron** (tanpa async_insert) supaya langsung queryable.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import clickhouse_connect
import psycopg
import pytest

from aegis.config import get_settings
from aegis.db.migrate import migrate_olap, migrate_oltp
from aegis.db.oltp import model_versions_repo, retrain_jobs_repo
from aegis.db.postgres import connection
from aegis.jobs.retrain import run_retrain

_N = 22  # per kelas (≥20 → LGBM dilatih)
_TRAFFIC_COLS = ["trx_id", "features", "decision", "final_score", "weboptin_status", "ts"]


def _ch():
    s = get_settings()
    return clickhouse_connect.get_client(
        host=s.clickhouse_host, port=s.clickhouse_port, username=s.clickhouse_user,
        password=s.clickhouse_password, database=s.clickhouse_db, connect_timeout=3,
    )


def _reachable() -> object | None:
    try:
        with psycopg.connect(get_settings().postgres_dsn, connect_timeout=3):
            pass
        return _ch()
    except Exception:
        return None


@pytest.fixture(scope="module")
def seeded():
    client = _reachable()
    if client is None:
        pytest.skip("PostgreSQL/ClickHouse tak terjangkau")
    s = get_settings()
    migrate_oltp(s)
    migrate_olap(s)

    old = datetime.now(UTC) - timedelta(days=30)  # > maturation window (7 hari)
    dec_rows, out_rows, ch_rows = [], [], []
    for i in range(_N):  # human: langganan sukses matang, tanpa komplain
        trx = f"h-{uuid.uuid4().hex[:12]}"
        dec_rows.append((trx, "allow", old))
        out_rows.append((trx, "subscription", "success", old))
        feats = {"automation_score": 0.05, "mouse_velocity_mean": 0.5 + i * 0.01,
                 "has_mouse": 1.0, "is_webview": 0.0}
        ch_rows.append([trx, json.dumps(feats), "allow", 0.1, "minted", old])
    for i in range(_N):  # robot: ada komplain
        trx = f"r-{uuid.uuid4().hex[:12]}"
        dec_rows.append((trx, "allow", old))
        out_rows.append((trx, "complaint", None, old))
        feats = {"automation_score": 0.95, "auto_webdriver": 1.0,
                 "mouse_velocity_mean": 0.01 * i, "is_webview": 1.0}
        ch_rows.append([trx, json.dumps(feats), "allow", 0.9, "minted", old])

    with connection() as conn, conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO decisions (trx_id, decision, created_at) VALUES (%s, %s, %s)",
            dec_rows,
        )
        cur.executemany(
            "INSERT INTO outcomes (trx_id, callback_type, charging_status, received_at) "
            "VALUES (%s, %s, %s, %s)",
            out_rows,
        )
    client.insert("traffic_events", ch_rows, column_names=_TRAFFIC_COLS)
    return True


def test_retrain_end_to_end(seeded) -> None:
    with connection() as conn:
        job_id = retrain_jobs_repo.create_job(conn)

    result = run_retrain(job_id)

    assert result["status"] == "done", result
    assert result["active"] is False  # AC-RETRAIN-01.2
    assert result["n_human"] >= _N and result["n_robot"] >= _N
    assert result["lgbm_trained"] is True
    assert result["algorithm"] == "isolation_forest+lightgbm"

    base = Path(get_settings().model_dir) / f"v{result['version']}"
    assert (base / "iso.pkl").exists()
    assert (base / "lgbm.pkl").exists()

    with connection() as conn:
        job = retrain_jobs_repo.get_job(conn, job_id)
    assert job["status"] == "done"

    # registrasi active=false; aktivasi = approval admin (model_versions_repo.activate)
    with connection() as conn:
        rows = {str(m["id"]): m for m in model_versions_repo.list_all(conn)}
    assert rows[result["model_id"]]["active"] is False

    with connection() as conn:
        activated = model_versions_repo.activate(conn, result["model_id"])
    assert activated["active"] is True
