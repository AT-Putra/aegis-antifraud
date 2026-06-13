"""Pytest global: cleanup data test agar DB dev tidak terkotori antar-run.

Masalah yang dicegah: test integrasi menulis ke Postgres dev (services, users, campaigns,
rule_configs, app_settings, model_versions, decisions, outcomes, feedback, devices,
retrain_jobs). Tanpa cleanup, baris menumpuk tiap `pytest` → menu admin dashboard penuh
sampah (mis. setting `k-xxxx`, config `{"a":1}`).

Strategi: session-scoped autouse fixture men-*snapshot* PK baseline tiap tabel SEBELUM test,
lalu di akhir sesi MENGHAPUS hanya baris yang BARU (PK di luar snapshot) — naming-agnostic,
hormati urutan FK (anak→induk). Idempoten & aman bila Postgres tak terjangkau (di-skip).
Tidak menyentuh baris baseline (admin bootstrap, default_timezone, rule_configs v1).
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


def _pg_conn():
    try:
        import psycopg

        return psycopg.connect(get_settings().postgres_dsn, connect_timeout=3)
    except Exception:
        return None


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_rows():
    """Snapshot PK baseline → jalankan sesi test → hapus baris baru (delta)."""
    conn = _pg_conn()
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

    yield  # ---- jalankan seluruh sesi test ----

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
