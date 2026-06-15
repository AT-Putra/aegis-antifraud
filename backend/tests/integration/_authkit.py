"""Helper auth test (ADR-015): bangun header cookie + CSRF untuk TestClient.

Sejak migrasi JWT localStorage→cookie httpOnly, dashboard tak lagi pakai header
`Authorization: Bearer`. Test memakai `auth_headers(...)` yang mengembalikan dict berisi
header `Cookie` (aegis_jwt + aegis_csrf) dan header `X-CSRF-Token` yang dipantulkan.
Header CSRF tak berbahaya pada GET (di-skip oleh verify_csrf), jadi satu dict ini bisa
dipakai untuk request GET maupun mutasi. Untuk menguji penolakan CSRF, pakai
`auth_cookies_only(...)` (tanpa header X-CSRF-Token).
"""

from __future__ import annotations

from aegis.security.jwt_auth import COOKIE_NAME as _JWT_COOKIE
from aegis.security.jwt_auth import CSRF_COOKIE_NAME, CSRF_HEADER, create_token

# Nilai CSRF deterministik untuk test (double-submit: cookie == header).
CSRF_TOKEN = "test-csrf-token"


def _cookie_header(token: str) -> str:
    return f"{_JWT_COOKIE}={token}; {CSRF_COOKIE_NAME}={CSRF_TOKEN}"


def auth_headers(username: str = "tester", role: str = "admin") -> dict:
    """Header lengkap (cookie + X-CSRF-Token) — cocok untuk GET maupun mutasi."""
    return {
        "Cookie": _cookie_header(create_token(username, role)),
        CSRF_HEADER: CSRF_TOKEN,
    }


def auth_cookies_only(username: str = "tester", role: str = "admin") -> dict:
    """Hanya cookie auth, TANPA header X-CSRF-Token → mutasi harus 403 (uji CSRF)."""
    return {"Cookie": _cookie_header(create_token(username, role))}
