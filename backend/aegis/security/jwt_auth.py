"""JWT untuk dashboard (`03 §2.1/§6`, ADR-015). HS256, login sederhana (tanpa refresh rilis-1).

Transport auth = httpOnly cookie `aegis_jwt` (tak terbaca JS → blast-radius XSS terbatas),
bukan Bearer/localStorage. Tradeoff cookie = rentan CSRF → proteksi double-submit token
(`verify_csrf`): SameSite=Strict + cookie `aegis_csrf` non-httpOnly yang dipantulkan klien
via header `X-CSRF-Token`. Lihat ADR-015 (supersede bagian auth ADR-013).
"""

from __future__ import annotations

import hmac
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, Request, Response, status

from aegis.config import get_settings

JWT_TTL_SECONDS = 8 * 3600
_ALGO = "HS256"

# Nama cookie & header (ADR-015). aegis_jwt = httpOnly; aegis_csrf = dibaca JS untuk dipantulkan.
COOKIE_NAME = "aegis_jwt"
CSRF_COOKIE_NAME = "aegis_csrf"
CSRF_HEADER = "X-CSRF-Token"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def create_token(sub: str, role: str) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=JWT_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(claims, get_settings().jwt_secret, algorithm=_ALGO)


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGO])


def require_role(*roles: str) -> Callable[..., dict]:
    """Dependency FastAPI: validasi JWT dari cookie + (opsional) batasi role.

    Token dibaca dari cookie httpOnly `aegis_jwt` (ADR-015), bukan header Bearer.
    Dipakai router T-12/T-15 (dashboard). API publik (scoring/callbacks) TIDAK pakai ini.
    """

    def dependency(request: Request) -> dict:
        token = request.cookies.get(COOKIE_NAME)
        if not token:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing token")
        try:
            claims = decode_token(token)
        except jwt.PyJWTError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc
        if roles and claims.get("role") not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
        return claims

    return dependency


def set_auth_cookies(response: Response, token: str) -> None:
    """Pasang cookie auth saat login (ADR-015).

    - `aegis_jwt`: httpOnly (tak terbaca JS), SameSite=Strict, Path=/, Max-Age=TTL.
    - `aegis_csrf`: NON-httpOnly (dibaca JS untuk dipantulkan via header), nilai acak.
    `Secure` aktif hanya di produksi (HTTPS); di dev (HTTP) tetap bisa login lokal.
    """
    secure = get_settings().is_production
    response.set_cookie(
        COOKIE_NAME, token, max_age=JWT_TTL_SECONDS, path="/",
        httponly=True, secure=secure, samesite="strict",
    )
    response.set_cookie(
        CSRF_COOKIE_NAME, secrets.token_urlsafe(32), max_age=JWT_TTL_SECONDS, path="/",
        httponly=False, secure=secure, samesite="strict",
    )


def clear_auth_cookies(response: Response) -> None:
    """Hapus kedua cookie auth saat logout (ADR-015). Atribut samasertakan saat set agar
    konsisten (beberapa browser cocokkan cookie hapus berdasar atribut, bukan hanya nama)."""
    secure = get_settings().is_production
    response.delete_cookie(COOKIE_NAME, path="/", secure=secure, samesite="strict")
    response.delete_cookie(CSRF_COOKIE_NAME, path="/", secure=secure, samesite="strict")


def verify_csrf(request: Request) -> None:
    """Dependency CSRF double-submit (ADR-015): cocokkan header `X-CSRF-Token` vs cookie.

    Hanya diberlakukan pada metode mutasi (POST/PUT/DELETE/PATCH); metode aman dilewati.
    Login dikecualikan (belum ada cookie) dengan tidak memasang dependency ini di sana.
    Perbandingan constant-time. Cocok dengan SameSite=Strict sebagai pertahanan berlapis.
    """
    if request.method in _SAFE_METHODS:
        return
    cookie = request.cookies.get(CSRF_COOKIE_NAME)
    header = request.headers.get(CSRF_HEADER)
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "csrf check failed")
