"""Ekstraksi fitur deterministik dari `FeatureInput` → dict numerik (TRD §4.3).

Fungsi tunggal ini dipakai di inference (scoring T-11) DAN training (retrain T-17)
sehingga fitur konsisten — cegah train/serve skew (ADR-008).
"""

from __future__ import annotations

from aegis.features.schema import FEATURE_ORDER, FeatureInput

_KNOWN_INAPP = {"facebook", "instagram", "tiktok", "line"}

# Platform desktop (navigator.platform) — token khas non-mobile. Android asli =
# "Linux armv8l"/"Linux aarch64"; desktop Linux = "Linux x86_64" (server/emulator).
_DESKTOP_PLATFORM_TOKENS = ("x86", "win", "mac", "wow64")
# Token hardware mobile (navigator.platform ARM) & keluarga GPU (webgl.renderer) — ADR-024.
_ARM_PLATFORM_TOKENS = ("arm", "aarch64", "armv")
_MOBILE_GPU_TOKENS = ("adreno", "mali", "powervr")  # GPU khas HP Android
_APPLE_GPU_TOKENS = ("apple",)  # GPU iOS
_NORMAL_COLOR_DEPTHS = {24, 30, 32}
_CLUSTER_K = 3  # ≥K device_id berbeda berbagi signature behavior identik = farm (ADR-021)

# timezone IANA (token pertama) → himpunan benua IP yang konsisten. Granularitas benua
# (heuristik; tak menangkap mismatch intra-benua) — ADR-020.
_TZ_CONTINENTS: dict[str, set[str]] = {
    "Africa": {"AF"},
    "America": {"NA", "SA"},
    "Antarctica": {"AN"},
    "Asia": {"AS"},
    "Atlantic": {"EU", "AF", "NA", "SA"},
    "Australia": {"OC"},
    "Europe": {"EU"},
    "Indian": {"AS", "AF", "OC"},
    "Pacific": {"OC", "NA"},
}


def _b(x: object) -> float:
    return 1.0 if x else 0.0


def _claims_mobile(device_info: dict, ua_data: dict) -> bool:
    """Device MENGAKU mobile (dari device-info terparse UA atau UA-CH `mobile`)."""
    if device_info.get("device_type") in ("mobile", "tablet"):
        return True
    if device_info.get("os") in ("Android", "iOS"):
        return True
    return ua_data.get("mobile") is True


def _infer_hw_class(fp) -> dict:
    """Kelas hardware yang DISIMPULKAN dari fingerprint (ADR-024). Murni — token string.

    `platform` ARM/`armv81`/`aarch64` & GPU Adreno/Mali/PowerVR = HP Android; GPU Apple = iOS.
    Dipakai bersama oleh deteksi mismatch dua-arah (klaim desktop vs hardware mobile, dan
    mismatch keluarga-OS) agar logika hardware tak terduplikasi.
    """
    platform = (fp.platform or "").lower()
    renderer = ((fp.webgl.renderer if fp.webgl else "") or "").lower()
    return {
        "arm_platform": any(t in platform for t in _ARM_PLATFORM_TOKENS),
        "mobile_gpu": any(g in renderer for g in _MOBILE_GPU_TOKENS),
        "apple_gpu": any(g in renderer for g in _APPLE_GPU_TOKENS),
        "touch": (fp.maxTouchPoints or 0) > 0,
    }


def _tz_geo_mismatch(timezone: str | None, continent: str | None) -> bool:
    """True bila benua timezone client tak konsisten dgn benua negara IP."""
    if not timezone or not continent:
        return False
    region = timezone.split("/", 1)[0]
    allowed = _TZ_CONTINENTS.get(region)
    if not allowed:
        return False  # region tak terpetakan → jangan tebak
    return continent not in allowed


def extract_features(inp: FeatureInput) -> dict[str, float]:
    fp = inp.signals.fingerprint
    beh = inp.signals.behavior
    auto = inp.signals.automation_hints
    integ = inp.signals.integrity
    attr = inp.signals.attribution
    be = fp.browser_environment
    ip = inp.ip_intel or {}
    hist = inp.device_history or {}
    di = inp.device_info or {}
    camp = inp.campaign or {}
    vel = inp.velocity or {}
    ua_data = fp.ua_data or {}

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
    velocity_mean = float(mouse.get("velocity_mean", 0) or 0)
    tap_count = float(touch.get("tap_count", 0) or 0)
    gesture_count = float(touch.get("gesture_count", 0) or 0)
    interaction_count = float(timing.get("interaction_count", 0) or 0)
    # Hardened (ADR-020): mouse-move ber-velocity 0 = sintetis → tak dihitung behavior.
    real_mouse = move_count > 0 and velocity_mean > 0
    no_behavior = _b(
        not real_mouse and tap_count == 0 and gesture_count == 0 and interaction_count == 0
    )

    # --- browser environment ---
    is_webview = bool(getattr(be, "is_webview", None))
    if not is_webview:
        webview_risk = 0.0
    elif getattr(be, "inapp_browser", None) in _KNOWN_INAPP:
        webview_risk = 0.3
    else:
        webview_risk = 1.0

    # --- konsistensi / anti-emulasi (ADR-020) ---
    max_touch = fp.maxTouchPoints
    platform = (fp.platform or "").lower()
    claims_mobile = _claims_mobile(di, ua_data)
    desktop_platform = any(t in platform for t in _DESKTOP_PLATFORM_TOKENS)
    ua_mobile_false = ua_data.get("mobile") is False
    # Klaim mobile tapi fingerprint bertentangan (tanpa touch/platform desktop/UA-CH non-mobile).
    ua_fp_inconsistent = _b(
        claims_mobile and (max_touch == 0 or desktop_platform or ua_mobile_false)
    )
    mouse_on_touchless = _b(move_count > 0 and max_touch == 0 and claims_mobile)

    # --- konsistensi hardware↔klaim DUA-ARAH (ADR-024) ---
    hw = _infer_hw_class(fp)
    hw_is_mobile = hw["arm_platform"] or hw["mobile_gpu"]
    # (1) Klaim non-mobile (desktop/UA-CH mobile=false) tapi hardware jelas mobile/Android.
    #     Basis = platform ARM ∥ GPU mobile (kuat & tak ambigu). Touch SENGAJA tak dipakai
    #     sebagai pemicu berdiri-sendiri: laptop 2-in-1 layar-sentuh = false-positive.
    claims_nonmobile = di.get("device_type") == "desktop" or ua_mobile_false
    fp_claims_desktop_but_mobile = _b(claims_nonmobile and hw_is_mobile)
    # (2) Mismatch keluarga-OS: klaim iOS tapi hardware Android, atau klaim Android tapi GPU Apple.
    os_claim = di.get("os")
    os_hw_family_mismatch = _b(
        (os_claim == "iOS" and (hw["arm_platform"] or hw["mobile_gpu"]) and not hw["apple_gpu"])
        or (os_claim == "Android" and hw["apple_gpu"])
    )

    color_depth = fp.screen.colorDepth if fp.screen else None
    color_depth_anomaly = _b(bool(color_depth) and color_depth not in _NORMAL_COLOR_DEPTHS)

    # --- entropi fingerprint & sinyal entropi-tinggi (ADR-025) ---
    has_audio = _b(fp.audio_hash)
    fonts_empty = not fp.fonts
    # Fingerprint "terlalu bersih": audio kosong DAN fonts kosong (khas emulator/headless).
    # Valid hanya bila collector pre-landing benar-benar mengisi audio/fonts (lihat ADR-025).
    low_fp_entropy = _b(not fp.audio_hash and fonts_empty)
    device_pixel_ratio = float(fp.screen.devicePixelRatio or 0.0) if fp.screen else 0.0
    languages_count = float(len(fp.languages or []))
    dwell_ms = float(timing.get("dwell_ms", 0) or 0)

    tz_geo_mismatch = _b(_tz_geo_mismatch(fp.timezone, ip.get("continent")))

    home_country = camp.get("home_country")
    expect_carrier = bool(camp.get("expect_mobile_carrier"))
    ip_country = ip.get("country")
    campaign_geo_mismatch = _b(
        (bool(home_country) and bool(ip_country) and ip_country != home_country)
        or (expect_carrier and not ip.get("is_mobile_carrier"))
    )

    # Behavioral-collision: ≥K device berbeda berbagi signature behavior identik (ADR-021).
    behavior_cluster = _b(float(vel.get("behavior_cluster_size", 0) or 0) >= _CLUSTER_K)

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
        "ip_tz_geo_mismatch": tz_geo_mismatch,
        "ip_reputation_bad": _b(ip.get("ip_reputation")),
        "ua_fp_inconsistent": ua_fp_inconsistent,
        "campaign_geo_mismatch": campaign_geo_mismatch,
        "color_depth_anomaly": color_depth_anomaly,
        "mouse_on_touchless": mouse_on_touchless,
        "fp_claims_desktop_but_mobile": fp_claims_desktop_but_mobile,
        "os_hw_family_mismatch": os_hw_family_mismatch,
        "low_fp_entropy": low_fp_entropy,
        "has_audio": has_audio,
        "device_pixel_ratio": device_pixel_ratio,
        "languages_count": languages_count,
        "dwell_ms": dwell_ms,
        "behavior_cluster": behavior_cluster,
        "referrer_present": _b(getattr(attr, "referrer", None)),
        "locale_consistent": _b(getattr(attr, "locale_consistent", None)),
        "device_event_count": float(hist.get("event_count", 0) or 0),
        "device_is_new": _b(hist.get("is_new")),
    }
    return feats


def feature_vector(features: dict[str, float]) -> list[float]:
    """Vektor terurut sesuai FEATURE_ORDER (input model)."""
    return [float(features.get(name, 0.0)) for name in FEATURE_ORDER]
