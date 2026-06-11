"""AC-SEC-04 (sebagian): rate-limit fixed-window (butuh Redis)."""

import uuid

import pytest

from aegis.db.redis import get_redis
from aegis.security.ratelimit import allow


def _redis_ok() -> bool:
    try:
        get_redis().ping()
        return True
    except Exception:
        return False


def test_rate_limit_blocks_after_limit() -> None:
    if not _redis_ok():
        pytest.skip("Redis tak terjangkau")
    key = f"test:{uuid.uuid4()}"
    assert allow(key, limit=3, window_seconds=60) is True   # 1
    assert allow(key, limit=3, window_seconds=60) is True   # 2
    assert allow(key, limit=3, window_seconds=60) is True   # 3
    assert allow(key, limit=3, window_seconds=60) is False  # 4 → blok
