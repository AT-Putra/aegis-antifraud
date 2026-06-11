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
    assert FEATURE_VERSION == "1"


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
