"""Helper API: client IP, error envelope {code,message} (`03 §2`), current-user deps."""

from __future__ import annotations

from ipaddress import ip_address, ip_network

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from aegis.config import get_settings
from aegis.db.oltp import users_repo
from aegis.db.postgres import connection
from aegis.security.jwt_auth import require_role

# Default: jaringan privat + loopback (Caddy di jaringan docker `aegis`).
_DEFAULT_TRUSTED = ("127.0.0.0/8", "::1/128", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")


def _trusted_networks():
    raw = get_settings().trusted_proxies.strip()
    nets = [n.strip() for n in raw.split(",") if n.strip()] if raw else _DEFAULT_TRUSTED
    out = []
    for n in nets:
        try:
            out.append(ip_network(n, strict=False))
        except ValueError:
            continue
    return out


def _is_trusted_peer(host: str | None) -> bool:
    if not host:
        return False
    try:
        addr = ip_address(host)
    except ValueError:
        return False
    return any(addr in net for net in _trusted_networks())


def client_ip(request: Request) -> str | None:
    """IP klien asli.

    X-Forwarded-For hanya dipercaya bila peer TCP langsung adalah proxy tepercaya
    (Caddy). Jika tidak (mis. api diakses langsung), pakai peer apa adanya — cegah
    spoofing XFF yang bisa mem-bypass rate-limit/login-throttle per-IP (T-20).
    """
    peer = request.client.host if request.client else None
    xff = request.headers.get("x-forwarded-for")
    if xff and _is_trusted_peer(peer):
        return xff.split(",")[0].strip()
    return peer


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
