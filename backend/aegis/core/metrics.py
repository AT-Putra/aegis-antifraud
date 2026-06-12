"""Metrik Prometheus ops (T-18, ADR-007). Kardinalitas dijaga rendah (tanpa service/campaign).

Di-expose di `GET /metrics` (internal-only; di-scrape Prometheus via jaringan docker).
"""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# HTTP
http_requests = Counter(
    "aegis_http_requests_total", "Total HTTP requests", ["route", "method", "status"]
)
http_latency = Histogram(
    "aegis_http_request_duration_seconds", "Latensi HTTP per route", ["route", "method"]
)
http_inflight = Gauge("aegis_http_inflight_requests", "Request sedang diproses")

# Scoring
decisions = Counter("aegis_decisions_total", "Keputusan scoring", ["decision"])
final_score = Histogram(
    "aegis_final_score", "Distribusi final_score",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)
score_latency = Histogram(
    "aegis_score_duration_seconds", "Durasi scoring (rules+model+blend)"
)

# CP web-opt-in
mint_latency = Histogram("aegis_cp_mint_duration_seconds", "Latensi mint web-opt-in ke CP")
mint_failures = Counter("aegis_cp_mint_failures_total", "Kegagalan mint web-opt-in", ["reason"])

# Callback billing & error
callbacks = Counter("aegis_callbacks_total", "Callback billing", ["type", "status"])
errors = Counter("aegis_errors_total", "Error tertangani", ["kind"])

CONTENT_TYPE = CONTENT_TYPE_LATEST


def render() -> bytes:
    return generate_latest()
