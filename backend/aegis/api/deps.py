"""Helper API: client IP, error envelope {code,message} (`03 §2`)."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


def client_ip(request: Request) -> str | None:
    """IP asli di belakang Caddy (X-Forwarded-For), fallback peer (K1)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message})
