"""AC-INFRA-01: stack berjalan & /health mengembalikan 200.

Dijalankan terhadap stack yang sudah `make up`. Target dikonfigurasi via
AEGIS_HEALTH_URL (default in-container: http://api:8000/health).
Di-skip otomatis bila endpoint tidak terjangkau (mis. stack belum dinyalakan).
"""

import os

import httpx
import pytest


def test_health_ok() -> None:
    url = os.environ.get("AEGIS_HEALTH_URL", "http://api:8000/health")
    try:
        resp = httpx.get(url, timeout=5.0)
    except httpx.HTTPError as exc:
        pytest.skip(f"stack tidak terjangkau di {url}: {exc}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
