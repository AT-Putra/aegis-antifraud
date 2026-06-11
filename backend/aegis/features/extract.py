"""Ekstraksi fitur deterministik dari `FeatureInput` → dict numerik (TRD §4.3).

Fungsi tunggal ini dipakai di inference (scoring T-11) DAN training (retrain T-17)
sehingga fitur konsisten — cegah train/serve skew (ADR-008).
"""

from __future__ import annotations

from aegis.features.schema import FEATURE_ORDER, FeatureInput

_KNOWN_INAPP = {"facebook", "instagram", "tiktok", "line"}


def _b(x: object) -> float:
    return 1.0 if x else 0.0


def extract_features(inp: FeatureInput) -> dict[str, float]:
    fp = inp.signals.fingerprint
    beh = inp.signals.behavior
    auto = inp.signals.automation_hints
    integ = inp.signals.integrity
    attr = inp.signals.attribution
    be = fp.browser_environment
    ip = inp.ip_intel or {}
    hist = inp.device_history or {}

    mouse = beh.mouse or {}
    timing = beh.timing or {}
    scroll = beh.scroll or {}
    touch = beh.touch or {}

    # --- automation ---
    webdriver = _b(getattr(auto, "webdriver", None))
    headless = _b(getattr(auto, "headless_hints", None))
    istrusted = getattr(auto, "isTrusted_cta", None)
    istrusted_false = 1.0 if istrusted is False else 0.0
    software_render = _b(getattr(auto, "webgl_software_render", None))
    globals_count = float(len(getattr(auto, "automation_globals", None) or []))
    viewport_anomaly = _b(getattr(auto, "viewport_anomaly", None))
    automation_score = (
        webdriver + headless + istrusted_false + software_render
        + viewport_anomaly + (1.0 if globals_count > 0 else 0.0)
    )

    # --- behavior ---
    move_count = float(mouse.get("move_count", 0) or 0)
    tap_count = float(touch.get("tap_count", 0) or 0)
    gesture_count = float(touch.get("gesture_count", 0) or 0)
    interaction_count = float(timing.get("interaction_count", 0) or 0)
    no_behavior = _b(
        move_count == 0 and tap_count == 0 and gesture_count == 0 and interaction_count == 0
    )

    # --- browser environment ---
    is_webview = bool(getattr(be, "is_webview", None))
    if not is_webview:
        webview_risk = 0.0
    elif getattr(be, "inapp_browser", None) in _KNOWN_INAPP:
        webview_risk = 0.3
    else:
        webview_risk = 1.0

    feats: dict[str, float] = {
        "auto_webdriver": webdriver,
        "auto_headless": headless,
        "auto_istrusted_false": istrusted_false,
        "auto_software_render": software_render,
        "auto_globals_count": globals_count,
        "auto_viewport_anomaly": viewport_anomaly,
        "automation_score": automation_score,
        "ever_visible": _b(getattr(integ, "ever_visible", None)),
        "iframe_embedded": _b(getattr(integ, "iframe_embedded", None)),
        "time_skew_abs_s": abs(float(getattr(integ, "time_skew_ms", 0) or 0)) / 1000.0,
        "touch_consistent": _b(getattr(integ, "touch_device_consistent", None)),
        "has_mouse": _b(move_count > 0),
        "mouse_velocity_mean": float(mouse.get("velocity_mean", 0) or 0),
        "mouse_direction_changes": float(mouse.get("direction_changes", 0) or 0),
        "scroll_depth_pct": float(scroll.get("depth_pct", 0) or 0),
        "tap_count": tap_count,
        "time_to_cta_ms": float(timing.get("time_to_cta_ms", 0) or 0),
        "interaction_count": interaction_count,
        "no_behavior": no_behavior,
        "has_canvas": _b(fp.canvas_hash),
        "has_webgl": _b(fp.webgl and fp.webgl.renderer),
        "fonts_count": float(len(fp.fonts or [])),
        "hardware_concurrency": float(fp.hardwareConcurrency or 0),
        "device_memory": float(fp.deviceMemory or 0),
        "is_webview": _b(is_webview),
        "webview_risk": webview_risk,
        "ip_is_datacenter": _b(ip.get("is_datacenter")),
        "ip_is_vpn_proxy_tor": _b(ip.get("vpn_proxy_tor")),
        "ip_is_mobile_carrier": _b(ip.get("is_mobile_carrier")),
        "ip_tz_geo_mismatch": _b(ip.get("tz_geo_mismatch")),
        "ip_reputation_bad": _b(ip.get("ip_reputation")),
        "referrer_present": _b(getattr(attr, "referrer", None)),
        "locale_consistent": _b(getattr(attr, "locale_consistent", None)),
        "device_event_count": float(hist.get("event_count", 0) or 0),
        "device_is_new": _b(hist.get("is_new")),
    }
    return feats


def feature_vector(features: dict[str, float]) -> list[float]:
    """Vektor terurut sesuai FEATURE_ORDER (input model)."""
    return [float(features.get(name, 0.0)) for name in FEATURE_ORDER]
