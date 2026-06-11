"""Input & versi fitur. `FEATURE_ORDER` = urutan stabil vektor model (K2)."""

from __future__ import annotations

from dataclasses import dataclass

from aegis.schemas.scoring import Signals

FEATURE_VERSION = "1"

# Urutan TETAP — model dilatih & meng-inference dengan urutan ini. Jangan ubah
# urutan/elemen tanpa menaikkan FEATURE_VERSION (cocokkan dengan model_versions).
FEATURE_ORDER: list[str] = [
    # automation
    "auto_webdriver", "auto_headless", "auto_istrusted_false", "auto_software_render",
    "auto_globals_count", "auto_viewport_anomaly", "automation_score",
    # integrity
    "ever_visible", "iframe_embedded", "time_skew_abs_s", "touch_consistent",
    # behavior
    "has_mouse", "mouse_velocity_mean", "mouse_direction_changes", "scroll_depth_pct",
    "tap_count", "time_to_cta_ms", "interaction_count", "no_behavior",
    # fingerprint presence
    "has_canvas", "has_webgl", "fonts_count", "hardware_concurrency", "device_memory",
    # browser environment
    "is_webview", "webview_risk",
    # ip intelligence
    "ip_is_datacenter", "ip_is_vpn_proxy_tor", "ip_is_mobile_carrier",
    "ip_tz_geo_mismatch", "ip_reputation_bad",
    # attribution & history
    "referrer_present", "locale_consistent", "device_event_count", "device_is_new",
]


@dataclass
class FeatureInput:
    """Input ternormalisasi. Sama untuk inference (dari request) & training (rekonstruksi)."""

    signals: Signals
    ip_intel: dict | None = None
    device_info: dict | None = None
    device_history: dict | None = None  # {"event_count": int, "is_new": bool}
