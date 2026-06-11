"""Runner migrasi idempoten untuk OLTP (PostgreSQL) & OLAP (ClickHouse).

Mencatat file yang sudah diterapkan di tabel `schema_migrations` per-DB lalu
hanya menjalankan file `.sql` baru, terurut. Aman dijalankan berulang (TRD §7).

Pakai: `python -m aegis.db.migrate`
"""

from __future__ import annotations

import re
from pathlib import Path

import clickhouse_connect
import psycopg

from aegis.config import Settings, get_settings

_OLTP_DIR = Path(__file__).parent / "oltp" / "migrations"
_OLAP_DIR = Path(__file__).parent / "olap" / "migrations"


def _statements(sql: str) -> list[str]:
    """Pecah skrip SQL menjadi statement, buang komentar. DDL polos (tanpa body PL/pgSQL)."""
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", "", sql)
    return [s.strip() for s in sql.split(";") if s.strip()]


def _sql_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.sql"))


def migrate_oltp(s: Settings) -> list[str]:
    applied: list[str] = []
    with psycopg.connect(s.postgres_dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "filename text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            conn.commit()
            cur.execute("SELECT filename FROM schema_migrations")
            done = {row[0] for row in cur.fetchall()}
            for f in _sql_files(_OLTP_DIR):
                if f.name in done:
                    continue
                for stmt in _statements(f.read_text(encoding="utf-8")):
                    cur.execute(stmt)
                cur.execute("INSERT INTO schema_migrations (filename) VALUES (%s)", (f.name,))
                conn.commit()
                applied.append(f.name)
    return applied


def migrate_olap(s: Settings) -> list[str]:
    applied: list[str] = []
    client = clickhouse_connect.get_client(
        host=s.clickhouse_host,
        port=s.clickhouse_port,
        username=s.clickhouse_user,
        password=s.clickhouse_password,
        database=s.clickhouse_db,
    )
    client.command(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(filename String, applied_at DateTime DEFAULT now()) "
        "ENGINE = MergeTree ORDER BY filename"
    )
    done = {row[0] for row in client.query("SELECT filename FROM schema_migrations").result_rows}
    for f in _sql_files(_OLAP_DIR):
        if f.name in done:
            continue
        for stmt in _statements(f.read_text(encoding="utf-8")):
            client.command(stmt)
        client.insert("schema_migrations", [[f.name]], column_names=["filename"])
        applied.append(f.name)
    return applied


def main() -> int:
    s = get_settings()
    oltp = migrate_oltp(s)
    olap = migrate_olap(s)
    print(f"OLTP applied: {oltp or 'none (up-to-date)'}")
    print(f"OLAP applied: {olap or 'none (up-to-date)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
