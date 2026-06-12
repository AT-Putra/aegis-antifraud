"""Helper API: client IP, error envelope {code,message} (`03 §2`), current-user deps."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from aegis.db.oltp import users_repo
from aegis.db.postgres import connection
from aegis.security.jwt_auth import require_role


def client_ip(request: Request) -> str | None:
    """IP asli di belakang Caddy (X-Forwarded-For), fallback peer (K1)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message})


_REQUIRE_ANY = require_role()


def _resolve(claims: dict) -> dict:
    with connection() as conn:
        user = users_repo.get_by_username(conn, claims.get("sub", ""))
    if user is None or not user["active"]:
        raise HTTPException(401, "user not found")
    return user


def current_user(claims: dict = Depends(_REQUIRE_ANY)) -> dict:
    """User terautentikasi (role apa pun). Dipakai endpoint user (mis. /users/me)."""
    return _resolve(claims)


def current_admin(claims: dict = Depends(_REQUIRE_ANY)) -> dict:
    """User admin (T-15: semua endpoint /v1/admin). Role efektif dibaca dari DB."""
    user = _resolve(claims)
    if user["role"] != "admin":
        raise HTTPException(403, "forbidden")
    return user
