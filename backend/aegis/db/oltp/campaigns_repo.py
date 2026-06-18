"""Repository tabel `campaigns` (T-21, F-16). Pre-landing portabel; CORS per-campaign."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

# Kolom publik (join slug service utk tampilan/atribusi).
_PUBLIC = (
    "c.id, c.slug, c.name, s.slug AS service, c.allowed_origins, c.allowed_countries, "
    "c.status, c.created_at, c.updated_at"
)
_FROM = "FROM campaigns c JOIN services s ON s.id = c.service_id"


def insert_campaign(
    conn: psycopg.Connection,
    *,
    slug: str,
    name: str,
    service_id: str,
    allowed_origins: list[str],
    allowed_countries: list[str],
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO campaigns (slug, name, service_id, allowed_origins, allowed_countries) "
            "VALUES (%s, %s, %s::uuid, %s, %s) RETURNING id",
            (slug, name, service_id, allowed_origins, allowed_countries),
        )
        return str(cur.fetchone()[0])


def get_by_id(conn: psycopg.Connection, campaign_id: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_PUBLIC} {_FROM} WHERE c.id = %s::uuid", (campaign_id,))
        return cur.fetchone()


def get_by_slug(conn: psycopg.Connection, slug: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_PUBLIC} {_FROM} WHERE c.slug = %s", (slug,))
        return cur.fetchone()


def list_all(conn: psycopg.Connection, service: str | None = None) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        if service:
            cur.execute(
                f"SELECT {_PUBLIC} {_FROM} WHERE s.slug = %s ORDER BY c.created_at",
                (service,),
            )
        else:
            cur.execute(f"SELECT {_PUBLIC} {_FROM} ORDER BY c.created_at")
        return cur.fetchall()


def active_origins(conn: psycopg.Connection) -> list[str]:
    """Union semua allowed_origins campaign aktif (untuk CORS dinamis D1)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT unnest(allowed_origins) FROM campaigns WHERE status = 'active'"
        )
        return [r[0] for r in cur.fetchall() if r[0]]


def update_campaign(
    conn: psycopg.Connection,
    campaign_id: str,
    *,
    name: str | None = None,
    allowed_origins: list[str] | None = None,
    allowed_countries: list[str] | None = None,
    status: str | None = None,
) -> dict | None:
    sets: list[str] = []
    params: list[object] = []
    for col, val in (
        ("name", name),
        ("allowed_origins", allowed_origins),
        ("allowed_countries", allowed_countries),
        ("status", status),
    ):
        if val is not None:
            sets.append(f"{col} = %s")  # nama kolom literal → aman
            params.append(val)
    if not sets:
        return get_by_id(conn, campaign_id)
    sets.append("updated_at = now()")
    params.append(campaign_id)
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE campaigns SET {', '.join(sets)} WHERE id = %s::uuid", params
        )
    return get_by_id(conn, campaign_id)
