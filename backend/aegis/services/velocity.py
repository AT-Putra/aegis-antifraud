"""Deteksi behavioral-collision (device farm replay) — velocity per signature perilaku.

Pola fraud (ADR-021): banyak `device_id`/IP BERBEDA tapi sinyal behavior IDENTIK sampai
milidetik (script memutar ulang satu template interaksi dgn fingerprint+IP acak). Tiap
request terlihat sempurna per-request → hanya terdeteksi lintas-request.

Signature dibangun dari behavior (timing entropi tinggi + mouse/scroll/touch). Redis ZSET
sliding-window menghitung jumlah `device_id` BERBEDA dgn signature identik per service.
Stateful → dihitung di API (di luar `extract_features` yang murni/skew-free, pola sama
`device_history`), nilainya disuntik ke `FeatureInput.velocity` lalu disimpan ke OLAP.

False-positive guard: signature HANYA dibuat bila timing (`time_to_cta_ms`+`dwell_ms`)
hadir & >0. Timing milidetik = entropi sangat tinggi → tabrakan antar-manusia mustahil;
traffic tanpa timing tak ikut diklaster (cegah mengelompokkan semua trafik 'tanpa behavior').
"""

from __future__ import annotations

import hashlib
import time

from aegis.db.redis import get_redis
from aegis.schemas.scoring import Behavior

WINDOW_SECONDS = 3600  # 60 menit (tunable)


def behavior_signature(behavior: Behavior | None) -> str | None:
    """Hash stabil dari template behavior, atau None bila timing entropi tak memadai."""
    if behavior is None:
        return None
    timing = behavior.timing or {}
    ttc = timing.get("time_to_cta_ms")
    dwell = timing.get("dwell_ms")
    if not ttc or not dwell:  # tanpa timing entropi → jangan klaster (FP guard)
        return None
    mouse = behavior.mouse or {}
    scroll = behavior.scroll or {}
    touch = behavior.touch or {}
    parts = (
        ttc, dwell, timing.get("interaction_count", 0),
        mouse.get("move_count", 0), round(float(mouse.get("velocity_mean", 0) or 0), 3),
        mouse.get("direction_changes", 0),
        scroll.get("depth_pct", 0),
        touch.get("tap_count", 0), touch.get("gesture_count", 0),
    )
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode()).hexdigest()[:16]  # noqa: S324 — bukan utk keamanan


def cluster_size(
    service: str,
    signature: str | None,
    device_id: str,
    *,
    window_seconds: int = WINDOW_SECONDS,
    now: float | None = None,
) -> int:
    """Catat device_id pada signature & kembalikan jumlah device_id BERBEDA dlm window.

    Best-effort: bila Redis tak terjangkau → 0 (jangan gagalkan scoring). ZSET member =
    device_id (dedup device sama yg reload), score = timestamp (sliding-window via prune).
    """
    if not signature:
        return 0
    now = now if now is not None else time.time()
    key = f"bsig:{service}:{signature}"
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.zadd(key, {device_id: now})
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        return int(pipe.execute()[2])
    except Exception:
        return 0
