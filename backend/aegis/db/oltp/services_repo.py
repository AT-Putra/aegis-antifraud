"""Repository tabel `services` (TRD §3 db/oltp). hmac_secret = BYTEA ciphertext."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

# Kolom publik (TANPA hmac_secret) — secret hanya diambil eksplisit via get_by_slug.
_PUBLIC = "id, slug, name, operator, cp_api_url, status, created_at, updated_at"


def insert_service(
    conn: psycopg.Connection,
    slug: str,
    name: str,
    operator: str | None,
    cp_api_url: str,
    hmac_secret: bytes,
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO services (slug, name, operator, cp_api_url, hmac_secret) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (slug, name, operator, cp_api_url, hmac_secret),
        )
        return str(cur.fetchone()[0])


def get_by_id(conn: psycopg.Connection, service_id: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_PUBLIC} FROM services WHERE id = %s", (service_id,))
        return cur.fetchone()


def get_by_slug(conn: psycopg.Connection, slug: str) -> dict | None:
    """Termasuk hmac_secret (untuk dekripsi server-side)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_PUBLIC}, hmac_secret FROM services WHERE slug = %s", (slug,))
        return cur.fetchone()


def list_all(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_PUBLIC} FROM services ORDER BY created_at")
        return cur.fetchall()


def update_service(
    conn: psycopg.Connection,
    service_id: str,
    *,
    name: str | None = None,
    operator: str | None = None,
    cp_api_url: str | None = None,
    hmac_secret: bytes | None = None,
    status: str | None = None,
) -> dict | None:
    sets: list[str] = []
    params: list[object] = []
    for col, val in (
        ("name", name),
        ("operator", operator),
        ("cp_api_url", cp_api_url),
        ("hmac_secret", hmac_secret),
        ("status", status),
    ):
        if val is not None:
            sets.append(f"{col} = %s")  # nama kolom literal (bukan input) → aman
            params.append(val)
    if not sets:
        return get_by_id(conn, service_id)
    sets.append("updated_at = now()")
    params.append(service_id)
    query = f"UPDATE services SET {', '.join(sets)} WHERE id = %s RETURNING {_PUBLIC}"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchone()
