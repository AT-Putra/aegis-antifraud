"""Repository tabel `decisions` (TRD §3 db/oltp). T-09: exists_by_trx (deteksi orphan);
insert keputusan diperluas di T-12."""

from __future__ import annotations

import psycopg


def exists_by_trx(conn: psycopg.Connection, trx_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM decisions WHERE trx_id = %s", (trx_id,))
        return cur.fetchone() is not None
