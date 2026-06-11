"""Entrypoint FastAPI Aegis.

Lifespan memuat konfigurasi scoring aktif + model aktif (cold-start → rules-only, K3)
sekali saat startup. Ganti model perlu restart (hot-reload = future).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aegis import __version__
from aegis.api import analytics, callbacks, scoring
from aegis.config import get_settings
from aegis.ml.loader import load_active_models
from aegis.scoring.config import load_active_config
from aegis.security.origins import allowed_origins

_log = logging.getLogger("aegis.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
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


app = FastAPI(title="Aegis Anti Fraud", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins() or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scoring.router)
app.include_router(callbacks.router)
app.include_router(analytics.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": get_settings().app_env, "version": __version__}
