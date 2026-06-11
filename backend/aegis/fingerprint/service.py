"""Orkestrasi identifikasi device: compute device_id → upsert Postgres → cache Redis."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aegis.db.oltp.devices_repo import upsert_device
from aegis.db.postgres import connection
from aegis.fingerprint.cache import get_cached, write_through
from aegis.fingerprint.device_id import canonical_components, compute_device_id
from aegis.schemas.scoring import Fingerprint


@dataclass
class DeviceRecord:
    device_id: str
    is_new: bool
    event_count: int
    first_seen: datetime
    last_seen: datetime
    seen_in_cache: bool


def lookup_or_register(fp: Fingerprint) -> DeviceRecord:
    device_id = compute_device_id(fp)
    components = canonical_components(fp)
    seen_in_cache = get_cached(device_id) is not None

    with connection() as conn:
        is_new, event_count, first_seen, last_seen = upsert_device(
            conn, device_id, device_id, components
        )

    write_through(device_id, event_count, first_seen, last_seen)
    return DeviceRecord(
        device_id=device_id,
        is_new=is_new,
        event_count=event_count,
        first_seen=first_seen,
        last_seen=last_seen,
        seen_in_cache=seen_in_cache,
    )
