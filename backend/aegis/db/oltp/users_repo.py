"""Repository tabel `users` (T-15: auth + user management). Password = argon2 hash."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

_PUBLIC = "id, username, role, active, timezone"


def get_by_username(conn: psycopg.Connection, username: str) -> dict | None:
    """Termasuk password_hash (untuk verifikasi login)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_PUBLIC}, password_hash FROM users WHERE username = %s", (username,)
        )
        return cur.fetchone()


def get_by_id(conn: psycopg.Connection, user_id: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_PUBLIC} FROM users WHERE id = %s::uuid", (user_id,))
        return cur.fetchone()


def list_all(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_PUBLIC} FROM users ORDER BY created_at")
        return cur.fetchall()


def count(conn: psycopg.Connection) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM users")
        return int(cur.fetchone()[0])


def insert_user(
    conn: psycopg.Connection, *, username: str, password_hash: str, role: str
) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) "
            "RETURNING id",
            (username, password_hash, role),
        )
        return str(cur.fetchone()[0])


def update_user(
    conn: psycopg.Connection,
    user_id: str,
    *,
    role: str | None = None,
    active: bool | None = None,
    password_hash: str | None = None,
) -> dict | None:
    sets: list[str] = []
    params: list[object] = []
    for col, val in (("role", role), ("active", active), ("password_hash", password_hash)):
        if val is not None:
            sets.append(f"{col} = %s")  # nama kolom literal → aman
            params.append(val)
    if not sets:
        return get_by_id(conn, user_id)
    params.append(user_id)
    query = f"UPDATE users SET {', '.join(sets)} WHERE id = %s::uuid RETURNING {_PUBLIC}"
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        return cur.fetchone()


def update_timezone(conn: psycopg.Connection, user_id: str, timezone: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"UPDATE users SET timezone = %s WHERE id = %s::uuid RETURNING {_PUBLIC}",
            (timezone, user_id),
        )
        return cur.fetchone()
