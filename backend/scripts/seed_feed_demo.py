"""Seed demo: 100 keputusan realistis lewat scoring engine ASLI → OLAP (feed/analytics).

Bukan insert karangan: tiap baris membangun Signals → FeatureInput, menjalankan
`score()` dengan config & models aktif (sama seperti /v1/score), lalu menulis via
`traffic_repo.write_event` (jalur data identik endpoint: traffic_events + decision_log).
final_score & score_breakdown yang muncul di feed = hasil engine sungguhan.

Jalankan di dalam container API:
    docker exec aegis-antifraud-api-1 sh -c 'cd /app && python scripts/seed_feed_demo.py 100'
"""

from __future__ import annotations

import random
import sys
import uuid

from aegis.db.olap import traffic_repo
from aegis.db.postgres import connection
from aegis.features.device_info import parse_device_info
from aegis.features.schema import FeatureInput
from aegis.ml.loader import load_active_models
from aegis.schemas.scoring import Signals
from aegis.scoring.config import load_active_config
from aegis.scoring.engine import score

RNG = random.Random(20260613)

# UA realistis per device-class (parse_device_info menurunkan browser/os/brand/model).
_UA = {
    "android": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
    "ios": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "desktop": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "fb_wv": "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Mobile Safari/537.36 "
    "[FB_IAB/FB4A;FBAV/450.0.0.0;]",
}


def _ip(kind: str) -> dict:
    """IP intelligence tersintesis (di endpoint diturunkan enrich_ip dari IP nyata)."""
    base = {
        "residential": {"country": "ID", "asn": 7713, "isp": "Telkom Indonesia",
                        "connection_type": "broadband"},
        "mobile": {"country": "ID", "asn": 23693, "isp": "Telkomsel",
                   "connection_type": "mobile", "is_mobile_carrier": True},
        "datacenter": {"country": "US", "asn": 14061, "isp": "DigitalOcean",
                       "connection_type": "hosting", "is_datacenter": True},
        "vpn": {"country": "SG", "asn": 9009, "isp": "M247",
                "connection_type": "hosting", "vpn_proxy_tor": True,
                "ip_reputation": "suspicious"},
    }[kind]
    return base


def _human_behavior() -> dict:
    """Behavior manusia: gerak mouse/tap & timing wajar (jitter agar tiap baris beda)."""
    return {
        "mouse": {
            "move_count": RNG.randint(40, 260),
            "velocity_mean": round(RNG.uniform(0.6, 2.4), 3),
            "direction_changes": RNG.randint(5, 40),
        },
        "touch": {"tap_count": RNG.randint(1, 8), "gesture_count": RNG.randint(0, 4)},
        "scroll": {"depth_pct": RNG.randint(20, 100)},
        "timing": {
            "interaction_count": RNG.randint(4, 20),
            "time_to_cta_ms": RNG.randint(1200, 9000),
        },
    }


def _no_behavior() -> dict:
    return {"mouse": {"move_count": 0}, "touch": {}, "scroll": {}, "timing": {}}


# (nama, bobot, builder) → builder mengembalikan (signals_dict, ip_kind, device_class)
def _scenarios() -> list[tuple[str, float, object]]:
    def human_clean():
        return ({
            "fingerprint": {"canvas_hash": uuid.uuid4().hex[:12],
                            "webgl": {"renderer": "Mali-G78"},
                            "hardwareConcurrency": 8, "deviceMemory": 6,
                            "fonts": ["Roboto", "Noto"], "timezone": "Asia/Jakarta",
                            "browser_environment": {"is_webview": False}},
            "behavior": _human_behavior(),
            "automation_hints": {"webdriver": False},
            "integrity": {"ever_visible": True, "touch_device_consistent": True},
            "attribution": {"referrer": "https://m.facebook.com", "locale_consistent": True},
        }, "residential", "android")

    def human_mobile():
        s, _, _ = human_clean()
        return (s, "mobile", "ios")

    def human_inapp():  # webview in-app dikenal (FB) → risiko rendah
        return ({
            "fingerprint": {"canvas_hash": uuid.uuid4().hex[:12],
                            "webgl": {"renderer": "Adreno 640"},
                            "hardwareConcurrency": 6,
                            "browser_environment": {"is_webview": True,
                                                    "inapp_browser": "facebook"}},
            "behavior": _human_behavior(),
            "automation_hints": {"webdriver": False},
            "integrity": {"ever_visible": True},
        }, "mobile", "fb_wv")

    def human_light_vpn():  # manusia pakai VPN → borderline (allow)
        s, _, _ = human_clean()
        return (s, "vpn", "desktop")

    def quiet_no_behavior():  # tak ada interaksi (allow, risk 0.2)
        return ({
            "fingerprint": {"canvas_hash": uuid.uuid4().hex[:12],
                            "webgl": {"renderer": "Intel"},
                            "browser_environment": {"is_webview": False}},
            "behavior": _no_behavior(),
            "automation_hints": {"webdriver": False},
            "integrity": {"ever_visible": True},
        }, "residential", "desktop")

    def dc_no_behavior():  # datacenter + sepi → block
        s, _, _ = quiet_no_behavior()
        return (s, "datacenter", "desktop")

    def vpn_no_behavior():  # vpn + sepi → block (0.4)
        s, _, _ = quiet_no_behavior()
        return (s, "vpn", "desktop")

    def webview_unknown_quiet():  # webview tak dikenal + sepi → block
        return ({
            "fingerprint": {"canvas_hash": uuid.uuid4().hex[:12],
                            "browser_environment": {"is_webview": True,
                                                    "inapp_browser": "unknown"}},
            "behavior": _no_behavior(),
            "automation_hints": {"webdriver": False},
            "integrity": {"ever_visible": False},
        }, "datacenter", "android")

    def viewport_anomaly_dc():  # anomali soft (bukan hard) + datacenter → block
        return ({
            "fingerprint": {"canvas_hash": uuid.uuid4().hex[:12],
                            "browser_environment": {"is_webview": False}},
            "behavior": _no_behavior(),
            "automation_hints": {"webdriver": False, "viewport_anomaly": True},
            "integrity": {"ever_visible": True},
        }, "datacenter", "desktop")

    def bot_webdriver():  # hard-block
        return ({
            "fingerprint": {"canvas_hash": uuid.uuid4().hex[:12],
                            "browser_environment": {"is_webview": False}},
            "behavior": _no_behavior(),
            "automation_hints": {"webdriver": True},
        }, "datacenter", "desktop")

    def bot_headless():
        return ({
            "fingerprint": {"canvas_hash": uuid.uuid4().hex[:12],
                            "browser_environment": {"is_webview": False}},
            "behavior": _no_behavior(),
            "automation_hints": {"webdriver": False, "headless_hints": True},
        }, "datacenter", "desktop")

    def bot_globals():
        return ({
            "fingerprint": {"canvas_hash": uuid.uuid4().hex[:12],
                            "browser_environment": {"is_webview": False}},
            "behavior": _no_behavior(),
            "automation_hints": {"automation_globals": ["__webdriver_evaluate", "cdc_"]},
        }, "vpn", "desktop")

    def bot_istrusted():
        return ({
            "fingerprint": {"canvas_hash": uuid.uuid4().hex[:12],
                            "browser_environment": {"is_webview": False}},
            "behavior": _human_behavior(),  # gerak ada tapi klik sintetis
            "automation_hints": {"webdriver": False, "isTrusted_cta": False},
        }, "residential", "desktop")

    def bot_software_render():
        return ({
            "fingerprint": {"canvas_hash": uuid.uuid4().hex[:12],
                            "webgl": {"renderer": "SwiftShader"},
                            "browser_environment": {"is_webview": False}},
            "behavior": _no_behavior(),
            "automation_hints": {"webdriver": False, "webgl_software_render": True},
        }, "datacenter", "desktop")

    return [
        ("human_clean", 22, human_clean),
        ("human_mobile", 14, human_mobile),
        ("human_inapp_webview", 10, human_inapp),
        ("human_light_vpn", 6, human_light_vpn),
        ("quiet_no_behavior", 8, quiet_no_behavior),
        ("datacenter_quiet", 6, dc_no_behavior),
        ("vpn_quiet", 5, vpn_no_behavior),
        ("webview_unknown_quiet", 5, webview_unknown_quiet),
        ("viewport_anomaly_dc", 4, viewport_anomaly_dc),
        ("bot_webdriver", 4, bot_webdriver),
        ("bot_headless", 3, bot_headless),
        ("bot_automation_globals", 3, bot_globals),
        ("bot_isTrusted_false", 3, bot_istrusted),
        ("bot_software_render", 2, bot_software_render),
    ]


def _active_pairs() -> list[tuple[str, str]]:
    """Pasangan (service_slug, campaign_slug) aktif dari OLTP untuk dimensi realistis."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT s.slug, c.slug FROM campaigns c JOIN services s ON s.id = c.service_id "
            "WHERE c.status = 'active' AND s.status = 'active' LIMIT 40"
        )
        return [(r[0], r[1]) for r in cur.fetchall()]


def main(n: int) -> int:
    cfg = load_active_config()
    if cfg is None:
        print("ERROR: config scoring tidak aktif", file=sys.stderr)
        return 1
    models, model_version = load_active_models()
    if model_version is not None:
        cfg.model_version = model_version

    pairs = _active_pairs() or [("svc-demo", "camp-demo")]
    scen = _scenarios()
    names = [s[0] for s in scen]
    weights = [s[1] for s in scen]
    sources = ["fb", "tiktok", "google", "organic", "ig"]

    tally: dict[str, int] = {"allow": 0, "block": 0}
    by_scen: dict[str, int] = {}
    for i in range(n):
        name, _, builder = RNG.choices(scen, weights=weights, k=1)[0]
        sig_dict, ip_kind, dev_class = builder()
        signals = Signals(**sig_dict)
        ip_intel = _ip(ip_kind)
        device_info = parse_device_info(_UA[dev_class], None)
        be = signals.fingerprint.browser_environment
        is_webview = bool(be and be.is_webview)

        feature_input = FeatureInput(
            signals=signals, ip_intel=ip_intel, device_info=device_info,
            device_history={"event_count": RNG.randint(0, 50), "is_new": RNG.random() < 0.4},
        )
        outcome = score(feature_input, config=cfg, models=models)

        svc, camp = RNG.choice(pairs)
        trx = f"demo-{uuid.uuid4().hex[:16]}"
        traffic_repo.write_event(
            trx_id=trx, device_id=f"dev-{uuid.uuid4().hex[:12]}",
            service=svc, campaign=camp,
            source=RNG.choice(sources), pub_id=str(RNG.randint(1, 9)),
            signals=signals.model_dump(),
            features={},  # fitur turunan tak diperlukan untuk feed; engine sudah skor
            ip_intel=ip_intel, decision=outcome.decision, final_score=outcome.final_score,
            weboptin_status=("na" if outcome.decision == "block" else "minted"),
            rules_version=outcome.rules_version, model_version=outcome.model_version,
            reason=outcome.reason, device_info=device_info, is_webview=is_webview,
            score_breakdown=outcome.score_breakdown,
        )
        tally[outcome.decision] = tally.get(outcome.decision, 0) + 1
        by_scen[name] = by_scen.get(name, 0) + 1

    print(f"seeded {n} keputusan → allow={tally['allow']} block={tally['block']}")
    for k in sorted(by_scen):
        print(f"  {k}: {by_scen[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 100))
