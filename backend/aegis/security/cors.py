"""CORS dinamis (D1, T-21): reflect Origin bila sah (global ∪ origin campaign aktif).

CORSMiddleware Starlette statik tak bisa tahu origin per-campaign (pre-landing portabel
di host eksternal). Middleware ini me-reflect Origin yang sah + tangani preflight OPTIONS.
Cek otoritatif per-campaign tetap di `/v1/session/init` (403 forbidden_origin).
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from aegis.security import origins

_METHODS = "GET, POST, PUT, OPTIONS"
_HEADERS = "Authorization, Content-Type, X-Aegis-Signature, X-Aegis-Timestamp, X-Aegis-Request-Id"


def _cors_headers(origin: str) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": _METHODS,
        "Access-Control-Allow-Headers": _HEADERS,
        "Access-Control-Max-Age": "600",
        "Vary": "Origin",
    }


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        allowed = origins.is_allowed_dynamic(origin)
        if request.method == "OPTIONS" and "access-control-request-method" in request.headers:
            # Preflight: 200 + header CORS bila origin sah, else 403 (tanpa header).
            if allowed:
                return Response(status_code=200, headers=_cors_headers(origin))
            return Response(status_code=403)
        response = await call_next(request)
        if allowed:
            for k, v in _cors_headers(origin).items():
                response.headers[k] = v
        return response
