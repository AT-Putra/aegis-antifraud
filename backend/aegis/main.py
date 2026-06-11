"""Entrypoint FastAPI Aegis (T-01 skeleton).

Hanya menyediakan health check agar container sehat & infra dapat diverifikasi.
Router scoring/callback/admin/analytics ditambahkan oleh task pemiliknya (T-12, T-14, T-15).
"""

from fastapi import FastAPI

from aegis import __version__
from aegis.config import get_settings

app = FastAPI(title="Aegis Anti Fraud", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "env": settings.app_env, "version": __version__}
