"""Klien Redis bersama (state stateless API, rate-limit, session nonce). TRD §7, ADR-003."""

from __future__ import annotations

import redis

from aegis.config import Settings, get_settings

_client: redis.Redis | None = None


def get_redis(settings: Settings | None = None) -> redis.Redis:
    global _client
    if _client is None:
        s = settings or get_settings()
        _client = redis.Redis(host=s.redis_host, port=s.redis_port, decode_responses=True)
    return _client
