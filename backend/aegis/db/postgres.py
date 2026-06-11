"""Helper koneksi PostgreSQL bersama (TRD §3/§7).

Koneksi singkat per-operasi (commit saat sukses, rollback saat error). Connection
pool (psycopg_pool) = optimasi masa depan; di 1–2 rps koneksi per-operasi cukup.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from aegis.config import Settings, get_settings


@contextmanager
def connection(settings: Settings | None = None) -> Iterator[psycopg.Connection]:
    s = settings or get_settings()
    conn = psycopg.connect(s.postgres_dsn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
