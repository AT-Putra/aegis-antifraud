"""Middleware metrik HTTP (T-18): count + latensi + in-flight. Route template (low-cardinality)."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from aegis.core import metrics


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        metrics.http_inflight.inc()
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            dur = time.perf_counter() - start
            metrics.http_inflight.dec()
            # Pola route ter-match (mis. /v1/analytics/decision/{trx_id}) → cegah ledakan label.
            route_obj = request.scope.get("route")
            route = getattr(route_obj, "path", request.url.path)
            metrics.http_latency.labels(route, request.method).observe(dur)
            metrics.http_requests.labels(route, request.method, str(status)).inc()
