"""Pytest global: cleanup data test agar DB dev tidak terkotori antar-run.

Masalah yang dicegah: test integrasi menulis ke Postgres dev (services, users, campaigns,
rule_configs, app_settings, model_versions, decisions, outcomes, feedback, devices,
retrain_jobs) DAN ke ClickHouse dev (traffic_events, decision_log, outcome_log,
feedback_log — mis. `test_stream_emits_event` menyemai baris ber-ts 2099). Tanpa cleanup,
baris menumpuk tiap `pytest` → menu admin & feed/analitik dashboard penuh sampah.

Strategi: session-scoped autouse fixture men-*snapshot* PK/key baseline tiap tabel SEBELUM
test, lalu di akhir sesi MENGHAPUS hanya baris yang BARU (key di luar snapshot) —
naming-agnostic. Postgres: hormati urutan FK (anak→induk). ClickHouse: hapus per-tabel
(tak ada FK) via mutation `ALTER TABLE ... DELETE`. Idempoten & aman bila DB tak terjangkau
(di-skip). Tidak menyentuh baris baseline (admin bootstrap, default_timezone, rule_configs
v1, serta data OLAP yang sudah ada sebelum sesi test — mis. seed demo dashboard).
"""

from __future__ import annotations

import pytest

from aegis.config import get_settings

# (tabel, kolom PK) terurut ANAK→INDUK (hapus anak dulu agar tak melanggar FK).
_TABLES: list[tuple[str, str]] = [
    ("feedback", "id"),
    ("outcomes", "id"),
    ("retrain_jobs", "id"),
    ("decisions", "id"),
    ("campaigns", "id"),
    ("model_versions", "id"),
    ("devices", "device_id"),
    ("services", "id"),
    ("rule_configs", "id"),
    ("app_settings", "key"),
    ("users", "id"),
]

# Tabel OLAP (ClickHouse) + kolom kunci untuk delta-delete. Tanpa FK → urutan bebas.
_CH_TABLES: list[tuple[str, str]] = [
    ("traffic_events", "trx_id"),
    ("decision_log", "trx_id"),
    ("outcome_log", "trx_id"),
    ("feedback_log", "id"),
]


def _pg_conn():
    try:
        import psycopg

        return psycopg.connect(get_settings().postgres_dsn, connect_timeout=3)
    except Exception:
        return None


def _ch_client():
    try:
        import clickhouse_connect

        s = get_settings()
        return clickhouse_connect.get_client(
            host=s.clickhouse_host, port=s.clickhouse_port, username=s.clickhouse_user,
            password=s.clickhouse_password, database=s.clickhouse_db, connect_timeout=3,
        )
    except Exception:
        return None


def _ch_snapshot(client) -> dict[str, set]:
    """Snapshot key baseline tiap tabel OLAP (baris yang sudah ada sebelum sesi test)."""
    snap: dict[str, set] = {}
    if client is None:
        return snap
    for table, key in _CH_TABLES:
        try:
            rows = client.query(f"SELECT DISTINCT {key} FROM {table}").result_rows  # noqa: S608
            snap[table] = {r[0] for r in rows}
        except Exception:
            pass  # tabel belum ada (migrasi belum jalan) → lewati
    return snap


def _ch_cleanup(client, baseline: dict[str, set]) -> None:
    """Hapus baris OLAP yang BARU (key di luar baseline) via mutation ALTER ... DELETE."""
    if client is None:
        return
    for table, key in _CH_TABLES:
        if table not in baseline:
            continue
        keep = baseline[table]
        try:
            if keep:
                client.command(
                    f"ALTER TABLE {table} DELETE WHERE {key} NOT IN %(keep)s",  # noqa: S608
                    parameters={"keep": list(keep)},
                )
            else:
                client.command(f"TRUNCATE TABLE {table}")  # noqa: S608
        except Exception:
            pass  # OLAP loss-tolerant; gagal hapus tak boleh menggagalkan sesi test


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_rows():
    """Snapshot PK/key baseline → jalankan sesi test → hapus baris baru (delta), OLTP + OLAP."""
    conn = _pg_conn()
    ch = _ch_client()
    if conn is None:  # Postgres tak ada → test integrasi akan skip; tak ada yg perlu dibersihkan.
        yield
        return

    baseline: dict[str, set] = {}
    try:
        with conn.cursor() as cur:
            for table, pk in _TABLES:
                try:
                    cur.execute(f"SELECT {pk} FROM {table}")  # noqa: S608 — identifier konstan internal
                    baseline[table] = {r[0] for r in cur.fetchall()}
                except Exception:
                    conn.rollback()  # tabel belum ada (migrasi belum jalan) → lewati
    finally:
        conn.close()
    ch_baseline = _ch_snapshot(ch)

    yield  # ---- jalankan seluruh sesi test ----

    _ch_cleanup(ch, ch_baseline)
    conn = _pg_conn()
    if conn is None:
        return
    try:
        with conn.cursor() as cur:
            for table, pk in _TABLES:
                if table not in baseline:
                    continue
                keep = baseline[table]
                try:
                    if keep:
                        cur.execute(
                            f"DELETE FROM {table} WHERE {pk} <> ALL(%s)",  # noqa: S608
                            (list(keep),),
                        )
                    else:
                        cur.execute(f"DELETE FROM {table}")  # noqa: S608
                except Exception:
                    conn.rollback()
            conn.commit()
            # Invarian scoring: harus ada TEPAT SATU rule_config aktif. Test admin kerap
            # menonaktifkan seed lalu mengaktifkan versi baru; setelah versi baru terhapus,
            # bisa tersisa NOL aktif → /v1/score 503. Pulihkan: aktifkan versi tertinggi.
            try:
                cur.execute("SELECT count(*) FROM rule_configs WHERE active")
                if cur.fetchone()[0] != 1:
                    cur.execute("UPDATE rule_configs SET active=false WHERE active")
                    cur.execute(
                        "UPDATE rule_configs SET active=true "
                        "WHERE version=(SELECT max(version) FROM rule_configs)"
                    )
                    conn.commit()
            except Exception:
                conn.rollback()
    finally:
        conn.close()
