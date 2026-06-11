"""AC-DATA-01: migrasi idempoten + entitas TRD §4 ada (OLTP & OLAP).

Self-contained: menjalankan migrasi lalu memverifikasi. Di-skip bila DB tak terjangkau.
"""

from __future__ import annotations

import clickhouse_connect
import psycopg
import pytest

from aegis.config import get_settings
from aegis.db.migrate import migrate_olap, migrate_oltp

_OLTP_TABLES = {
    "users", "app_settings", "services", "devices", "decisions",
    "outcomes", "rule_configs", "model_versions", "feedback",
}
_OLAP_TABLES = {"traffic_events", "decision_log"}
_DECISION_COLS = {"service_id", "source", "pub_id", "weboptin_status", "weboptin_host"}


def _pg_reachable(s) -> bool:
    try:
        with psycopg.connect(s.postgres_dsn, connect_timeout=3):
            return True
    except Exception:
        return False


def test_oltp_idempotent_and_tables() -> None:
    s = get_settings()
    if not _pg_reachable(s):
        pytest.skip("PostgreSQL tak terjangkau")
    migrate_oltp(s)
    assert migrate_oltp(s) == [], "migrasi OLTP harus idempoten (run kedua kosong)"
    with psycopg.connect(s.postgres_dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        tables = {r[0] for r in cur.fetchall()}
        assert _OLTP_TABLES <= tables
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name='decisions'"
        )
        cols = {r[0] for r in cur.fetchall()}
        assert _DECISION_COLS <= cols
        # seed terisi
        cur.execute("SELECT value FROM app_settings WHERE key='default_timezone'")
        assert cur.fetchone()[0] == "Asia/Jakarta"
        cur.execute("SELECT count(*) FROM rule_configs WHERE active")
        assert cur.fetchone()[0] >= 1


def test_olap_idempotent_and_tables() -> None:
    s = get_settings()
    try:
        client = clickhouse_connect.get_client(
            host=s.clickhouse_host, port=s.clickhouse_port,
            username=s.clickhouse_user, password=s.clickhouse_password, database=s.clickhouse_db,
            connect_timeout=3,
        )
    except Exception:
        pytest.skip("ClickHouse tak terjangkau")
    migrate_olap(s)
    assert migrate_olap(s) == [], "migrasi OLAP harus idempoten (run kedua kosong)"
    rows = client.query("SHOW TABLES").result_rows
    tables = {r[0] for r in rows}
    assert _OLAP_TABLES <= tables
