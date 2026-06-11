"""AC-SCORE (config): load_active_config membaca rule_config aktif (seed v1)."""

import psycopg
import pytest

from aegis.config import get_settings
from aegis.scoring.config import load_active_config


def _reachable() -> bool:
    try:
        with psycopg.connect(get_settings().postgres_dsn, connect_timeout=3):
            return True
    except Exception:
        return False


def test_load_active_config() -> None:
    if not _reachable():
        pytest.skip("PostgreSQL tak terjangkau")
    cfg = load_active_config()
    assert cfg.version >= 1
    assert 0.0 <= cfg.threshold <= 1.0
    assert "rules" in cfg.blend_weights
