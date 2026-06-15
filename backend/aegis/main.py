"""Entrypoint FastAPI Aegis.

Lifespan memuat konfigurasi scoring aktif + model aktif (cold-start → rules-only, K3)
sekali saat startup. Ganti model perlu restart (hot-reload = future).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response

from aegis import __version__
from aegis.api import admin, analytics, auth, callbacks, scoring
from aegis.config import get_settings, is_weak_secret
from aegis.core import metrics
from aegis.core.logging import setup_logging
from aegis.core.middleware import MetricsMiddleware
from aegis.db.oltp import users_repo
from aegis.db.postgres import connection
from aegis.ml.loader import load_active_models
from aegis.scoring.config import load_active_config
from aegis.security.cors import DynamicCORSMiddleware
from aegis.security.passwords import hash_password

setup_logging()

_log = logging.getLogger("aegis.startup")


def _bootstrap_admin() -> None:
    """Buat admin awal bila tabel users kosong (T-15, K2). Idempoten."""
    s = get_settings()
    if not (s.admin_bootstrap_username and s.admin_bootstrap_password):
        return
    # T-20: di produksi, tolak bootstrap dgn kredensial lemah/default — jangan
    # diam-diam membuat admin yang mudah ditebak. Gagal startup agar terlihat.
    if s.is_production and (
        is_weak_secret(s.admin_bootstrap_password) or is_weak_secret(s.admin_bootstrap_username)
    ):
        raise RuntimeError(
            "APP_ENV="
            f"{s.app_env}: ADMIN_BOOTSTRAP_USERNAME/PASSWORD lemah atau default. "
            "Set username non-generik & password acak kuat (≥32 karakter, tanpa pola "
            "'change-me/dev-/admin/password/secret') sebelum bootstrap di produksi."
        )
    try:
        with connection() as conn:
            if users_repo.count(conn) > 0:
                return
            users_repo.insert_user(
                conn,
                username=s.admin_bootstrap_username,
                password_hash=hash_password(s.admin_bootstrap_password),
                role="admin",
            )
        _log.info("bootstrap: admin '%s' dibuat", s.admin_bootstrap_username)
    except Exception as exc:  # noqa: BLE001
        _log.error("bootstrap admin gagal: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings().validate_production()  # T-20 gate: fail-fast secret lemah di prod
    _bootstrap_admin()
    try:
        app.state.config = load_active_config()
    except Exception as exc:  # noqa: BLE001
        _log.error("gagal memuat rule_config aktif: %s", exc)
        app.state.config = None

    models, model_version = load_active_models()
    if app.state.config is not None and model_version is not None:
        app.state.config.model_version = model_version
    app.state.models = models
    _log.info("startup: config=%s model_version=%s", bool(app.state.config), model_version)
    yield


# T-20: matikan /docs, /redoc, /openapi.json di luar development (defense-in-depth —
# kurangi permukaan recon bila topologi ingress berubah / port ter-publish tak sengaja).
_docs_kwargs = (
    {"docs_url": None, "redoc_url": None, "openapi_url": None}
    if get_settings().is_production
    else {}
)
app = FastAPI(
    title="Aegis Anti Fraud", version=__version__, lifespan=lifespan, **_docs_kwargs
)

app.add_middleware(DynamicCORSMiddleware)  # CORS per-campaign (D1, F-16)
app.add_middleware(MetricsMiddleware)  # metrik HTTP (T-18) — outermost

app.include_router(scoring.router)
app.include_router(callbacks.router)
app.include_router(analytics.router)
app.include_router(auth.router)
app.include_router(admin.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": get_settings().app_env, "version": __version__}


@app.get("/metrics")
def metrics_endpoint() -> Response:
    """Prometheus metrics (internal-only; di-scrape via jaringan docker, bukan lewat Caddy)."""
    return Response(content=metrics.render(), media_type=metrics.CONTENT_TYPE)
