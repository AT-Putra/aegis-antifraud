"""Whitelist origin pre-landing (`03 §8`). CORS ditegakkan di api (T-12)."""

from __future__ import annotations

from aegis.config import get_settings


def allowed_origins() -> list[str]:
    raw = get_settings().allowed_origins
    return [o.strip() for o in raw.split(",") if o.strip()]


def is_allowed_origin(origin: str | None) -> bool:
    return bool(origin) and origin in allowed_origins()
