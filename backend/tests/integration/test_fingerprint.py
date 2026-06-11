"""AC-FP-01.2: lookup_or_register upsert + dedup + cache (Postgres + Redis)."""

import uuid

import psycopg
import pytest

from aegis.config import get_settings
from aegis.fingerprint.cache import get_cached
from aegis.fingerprint.device_id import compute_device_id
from aegis.fingerprint.service import lookup_or_register
from aegis.schemas.scoring import Fingerprint


def _reachable() -> bool:
    s = get_settings()
    try:
        with psycopg.connect(s.postgres_dsn, connect_timeout=3):
            return True
    except Exception:
        return False


def _unique_fp() -> Fingerprint:
    # canvas_hash unik per run agar device_id baru (DB persisten antar test run)
    return Fingerprint(
        canvas_hash=f"canvas-{uuid.uuid4()}",
        audio_hash="a1",
        timezone="Asia/Jakarta",
        languages=["id-ID"],
        platform="Linux",
        hardwareConcurrency=8,
    )


def test_register_then_dedup_and_cache() -> None:
    if not _reachable():
        pytest.skip("PostgreSQL tak terjangkau")
    fp = _unique_fp()
    device_id = compute_device_id(fp)

    first = lookup_or_register(fp)
    assert first.device_id == device_id
    assert first.is_new is True
    assert first.event_count == 1

    second = lookup_or_register(fp)
    assert second.is_new is False
    assert second.event_count == 2

    cached = get_cached(device_id)
    assert cached is not None and cached["event_count"] == 2
