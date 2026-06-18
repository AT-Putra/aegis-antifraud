"""AC-FEAT-01: ekstraksi deterministik, skew-free, sanity bot vs human."""

from aegis.features.extract import extract_features, feature_vector
from aegis.features.schema import FEATURE_ORDER, FEATURE_VERSION, FeatureInput
from aegis.schemas.scoring import Signals

_HUMAN = {
    "fingerprint": {
        "canvas_hash": "c1",
        "webgl": {"renderer": "Mali-G78"},
        "fonts": ["Arial", "Roboto"],
        "hardwareConcurrency": 8,
        "deviceMemory": 4,
        "browser_environment": {"is_webview": False},
    },
    "behavior": {
        "mouse": {"move_count": 120, "velocity_mean": 1.4, "direction_changes": 18},
        "scroll": {"depth_pct": 70},
        "touch": {"tap_count": 3},
        "timing": {"time_to_cta_ms": 5200, "interaction_count": 9},
    },
    "automation_hints": {"webdriver": False},
    "integrity": {"ever_visible": True, "touch_device_consistent": True},
    "attribution": {"referrer": "https://m.facebook.com", "locale_consistent": True},
}

_BOT = {
    "fingerprint": {
        "canvas_hash": "c1",
        "browser_environment": {"is_webview": True, "inapp_browser": None},
    },
    "behavior": {
        "mouse": {"move_count": 0},
        "touch": {"tap_count": 0},
        "timing": {"interaction_count": 0},
    },
    "automation_hints": {
        "webdriver": True,
        "headless_hints": True,
        "isTrusted_cta": False,
        "webgl_software_render": True,
        "automation_globals": ["_phantom", "$cdc_"],
        "viewport_anomaly": True,
    },
    "integrity": {"ever_visible": False, "iframe_embedded": True},
}


def _inp(sig: dict, **kw) -> FeatureInput:
    return FeatureInput(signals=Signals(**sig), **kw)


def test_deterministic() -> None:
    a = extract_features(_inp(_HUMAN))
    b = extract_features(_inp(_HUMAN))
    assert a == b


def test_keys_match_feature_order() -> None:
    feats = extract_features(_inp(_HUMAN))
    assert set(feats.keys()) == set(FEATURE_ORDER)
    assert len(feature_vector(feats)) == len(FEATURE_ORDER)
    assert FEATURE_VERSION == "2"


def test_skew_free_inference_vs_training_path() -> None:
    # "inference": Signals dari request; "training": rekonstruksi dari dict tersimpan.
    stored = dict(_HUMAN)  # ala signals JSON di traffic_events
    ip = {"is_datacenter": False}
    inference = extract_features(_inp(_HUMAN, ip_intel=ip))
    training = extract_features(FeatureInput(signals=Signals(**stored), ip_intel=ip))
    assert inference == training


def test_bot_has_high_automation_low_behavior() -> None:
    bot = extract_features(_inp(_BOT))
    human = extract_features(_inp(_HUMAN))
    assert bot["automation_score"] >= 5.0
    assert bot["no_behavior"] == 1.0
    assert bot["webview_risk"] == 1.0
    assert human["automation_score"] == 0.0
    assert human["no_behavior"] == 0.0
    assert human["has_mouse"] == 1.0


def test_ip_features_from_intel() -> None:
    feats = extract_features(_inp(_HUMAN, ip_intel={
        "is_datacenter": True, "vpn_proxy_tor": True, "is_mobile_carrier": False,
    }))
    assert feats["ip_is_datacenter"] == 1.0
    assert feats["ip_is_vpn_proxy_tor"] == 1.0
    assert feats["ip_is_mobile_carrier"] == 0.0


# --- Fitur konsistensi / anti-emulasi (ADR-020) ---

# Emulator server ber-UA mobile (pola 7 suspect /root/data-fraud): klaim Android mobile
# tapi fingerprint = desktop Linux tanpa touch, colorDepth ganjil, behavior sintetis.
_EMU_ANDROID = {
    "fingerprint": {
        "canvas_hash": "b9815f82",
        "screen": {"width": 412, "height": 869, "colorDepth": 16, "devicePixelRatio": 3.5},
        "timezone": "Europe/Amsterdam",
        "platform": "Linux x86_64",
        "maxTouchPoints": 0,
        "ua_data": {"mobile": False, "platform": ""},
        "browser_environment": {"is_webview": False},
    },
    "behavior": {
        "mouse": {"move_count": 1, "velocity_mean": 0, "direction_changes": 0},  # sintetis
        "scroll": {"depth_pct": 100},
        "touch": {"tap_count": 0},
        "timing": {"interaction_count": 0, "dwell_ms": 7423, "time_to_cta_ms": 6622},
    },
    "automation_hints": {"isTrusted_cta": True},  # bot set isTrusted=true utk hindari hard-rule
}


def _emu_feats(**kw) -> dict:
    return extract_features(_inp(
        _EMU_ANDROID,
        ip_intel={"country": "DE", "continent": "EU", "asn": 24940,
                  "is_datacenter": True, "is_mobile_carrier": False},
        device_info={"os": "Android", "device_type": "mobile", "browser": "Chrome"},
        **kw,
    ))


def test_ua_fp_inconsistent_mobile_claim_no_touch() -> None:
    feats = _emu_feats()
    assert feats["ua_fp_inconsistent"] == 1.0  # klaim mobile + maxTouchPoints=0 + platform desktop
    assert feats["mouse_on_touchless"] == 1.0  # mouse-move di device klaim-mobile tanpa touch


def test_no_behavior_resists_synthetic_mouse() -> None:
    # 1 mouse-move ber-velocity 0 = sintetis → no_behavior TETAP 1 (bypass tertutup, ADR-020).
    feats = _emu_feats()
    assert feats["no_behavior"] == 1.0
    assert feats["has_mouse"] == 1.0  # has_mouse tetap mencerminkan move_count>0 (apa adanya)


def test_color_depth_anomaly() -> None:
    assert _emu_feats()["color_depth_anomaly"] == 1.0  # colorDepth=16 (∉ {24,30,32})
    normal = extract_features(_inp({
        "fingerprint": {"screen": {"colorDepth": 24}}, "behavior": {},
    }))
    assert normal["color_depth_anomaly"] == 0.0


def test_tz_geo_mismatch_continent() -> None:
    # Europe/Amsterdam vs IP benua EU → konsisten (TIDAK mismatch) — sesuai 7 suspect.
    assert _emu_feats()["ip_tz_geo_mismatch"] == 0.0
    # timezone Asia tapi IP benua EU → mismatch.
    sig = dict(_EMU_ANDROID)
    sig["fingerprint"] = {**_EMU_ANDROID["fingerprint"], "timezone": "Asia/Jakarta"}
    feats = extract_features(_inp(sig, ip_intel={"country": "DE", "continent": "EU"}))
    assert feats["ip_tz_geo_mismatch"] == 1.0


def test_campaign_geo_mismatch_expectation() -> None:
    # Campaign Telkomsel(ID, carrier) vs IP datacenter Jerman → mismatch.
    feats = _emu_feats(campaign={"home_country": "ID", "expect_mobile_carrier": True})
    assert feats["campaign_geo_mismatch"] == 1.0
    # Tanpa ekspektasi campaign → tanpa sinyal.
    assert _emu_feats(campaign={})["campaign_geo_mismatch"] == 0.0


def test_emulated_android_scores_block() -> None:
    from aegis.scoring.rules import evaluate_rules
    feats = _emu_feats(campaign={"home_country": "ID", "expect_mobile_carrier": True})
    rr = evaluate_rules(feats, {})
    assert rr.rules_risk >= 0.3  # > ambang default → BLOCK (sebelumnya lolos = 0)


# --- Velocity / behavioral-collision (ADR-021) ---

# Pola suspect2: fingerprint "sempurna" (Android ARM asli, touch, locale ID, IP Telkomsel)
# → semua fitur konsistensi 0; HANYA terdeteksi via cluster perilaku lintas-device.
_GENUINE_LOOKING = {
    "fingerprint": {
        "canvas_hash": "561298c9",
        "webgl": {"renderer": "Mali-G52", "vendor": "ARM"},
        "screen": {"width": 360, "height": 740, "colorDepth": 24, "devicePixelRatio": 2},
        "timezone": "Asia/Jakarta",
        "platform": "Linux aarch64",
        "maxTouchPoints": 1,
        "languages": ["id-ID", "id", "en"],
        "ua_data": {"mobile": True, "platform": "Android"},
        "browser_environment": {"is_webview": False},
    },
    "behavior": {
        "timing": {"time_to_cta_ms": 170112, "dwell_ms": 172205, "interaction_count": 1},
        "mouse": {"move_count": 1, "velocity_mean": 0, "direction_changes": 0},
        "scroll": {"depth_pct": 100},
        "touch": {"tap_count": 1},
    },
    "automation_hints": {"isTrusted_cta": True},
    "integrity": {"ever_visible": True, "touch_device_consistent": True},
    "attribution": {"referrer": None, "locale_consistent": True},
}
_TELKOMSEL_IP = {"country": "ID", "continent": "AS", "asn": 23693,
                 "isp": "PT. Telekomunikasi Selular", "is_mobile_carrier": True}


def test_genuine_looking_passes_per_request() -> None:
    # Tanpa konteks velocity → semua fitur konsistensi 0 (per-request memang terlihat sah).
    from aegis.scoring.rules import evaluate_rules
    feats = extract_features(_inp(_GENUINE_LOOKING, ip_intel=_TELKOMSEL_IP,
                                  device_info={"os": "Android", "device_type": "mobile"},
                                  campaign={"home_country": "ID", "expect_mobile_carrier": True}))
    assert feats["ua_fp_inconsistent"] == 0.0
    assert feats["campaign_geo_mismatch"] == 0.0
    assert feats["behavior_cluster"] == 0.0
    assert evaluate_rules(feats, {}).rules_risk < 0.3  # lolos per-request (inilah gap-nya)


def test_behavior_cluster_blocks_farm() -> None:
    # Saat velocity mendeteksi ≥K device identik → behavior_cluster=1 → BLOCK.
    from aegis.scoring.rules import evaluate_rules
    feats = extract_features(_inp(_GENUINE_LOOKING, ip_intel=_TELKOMSEL_IP,
                                  device_info={"os": "Android", "device_type": "mobile"},
                                  campaign={"home_country": "ID", "expect_mobile_carrier": True},
                                  velocity={"behavior_cluster_size": 3}))
    assert feats["behavior_cluster"] == 1.0
    assert evaluate_rules(feats, {}).rules_risk >= 0.3  # farm tertangkap

    # Di bawah K (mis. 2) → belum di-flag.
    feats2 = extract_features(_inp(_GENUINE_LOOKING, velocity={"behavior_cluster_size": 2}))
    assert feats2["behavior_cluster"] == 0.0
