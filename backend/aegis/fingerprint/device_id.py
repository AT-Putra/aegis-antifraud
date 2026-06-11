"""Hitung `device_id` deterministik (ADR-004) dari subset stabil fingerprint (TRD §4.3).

Subset: Canvas + WebGL renderer/vendor + Audio + screen + fonts + timezone +
hardwareConcurrency + deviceMemory + platform + languages. Kanonikal → stabil
untuk perangkat yang sama (fonts di-sort; urutan languages dipertahankan karena bermakna).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from aegis.schemas.scoring import Fingerprint


def canonical_components(fp: Fingerprint) -> dict[str, Any]:
    screen = fp.screen
    webgl = fp.webgl
    return {
        "canvas_hash": fp.canvas_hash,
        "audio_hash": fp.audio_hash,
        "webgl_vendor": webgl.vendor if webgl else None,
        "webgl_renderer": webgl.renderer if webgl else None,
        "screen": (
            [screen.width, screen.height, screen.colorDepth, screen.devicePixelRatio]
            if screen
            else None
        ),
        "fonts": sorted(fp.fonts) if fp.fonts else None,
        "timezone": fp.timezone,
        "languages": fp.languages,
        "hardwareConcurrency": fp.hardwareConcurrency,
        "deviceMemory": fp.deviceMemory,
        "platform": fp.platform,
    }


def compute_device_id(fp: Fingerprint) -> str:
    blob = json.dumps(
        canonical_components(fp), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(blob.encode()).hexdigest()
