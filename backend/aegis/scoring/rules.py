"""Rules engine (murni): hard-override + skor risiko kontinu. Default tuning = TQ-02.

`SOFT_FACTORS` & `_hard_triggers()` adalah *sumber tunggal* bobot formula + logika
hard-rule, dipakai ulang oleh `scoring/explain.py` agar penjelasan audit tak bisa
melenceng dari skor yang sesungguhnya dihitung di sini.
"""

from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_HARD_RULES = (
    "webdriver",
    "headless",
    "automation_globals",
    "isTrusted_false",
    "software_render",
)

# Faktor skor risiko kontinu: (nama_fitur, label, bobot). Sumber tunggal formula —
# `rules_risk = min(1.0, Σ bobot·nilai)`. JANGAN duplikasi bobot di tempat lain.
SOFT_FACTORS: tuple[tuple[str, str, float], ...] = (
    ("automation_score", "Skor automasi", 0.2),
    ("webview_risk", "Risiko WebView", 0.3),
    ("ip_is_datacenter", "IP datacenter", 0.3),
    ("ip_is_vpn_proxy_tor", "IP VPN/Proxy/Tor", 0.2),
    ("no_behavior", "Tanpa interaksi", 0.2),
)

# Spesifikasi hard-rule: nama → (fitur, predikat). Predikat True → rule terpicu.
_HARD_SPECS: dict[str, tuple[str, object]] = {
    "webdriver": ("auto_webdriver", lambda v: bool(v)),
    "headless": ("auto_headless", lambda v: bool(v)),
    "automation_globals": ("auto_globals_count", lambda v: (v or 0) > 0),
    "isTrusted_false": ("auto_istrusted_false", lambda v: bool(v)),
    "software_render": ("auto_software_render", lambda v: bool(v)),
}


@dataclass
class RuleResult:
    hard_block: bool
    triggered: list[str]
    rules_risk: float


def enabled_hard_rules(params: dict | None = None) -> set[str]:
    """Himpunan hard-rule aktif menurut config (default = semua)."""
    params = params or {}
    return set(params.get("hard_rules", _DEFAULT_HARD_RULES))


def _hard_triggers(features: dict, enabled: set[str]) -> list[str]:
    """Hard-rule yang terpicu, urut deterministik sesuai `_HARD_SPECS`."""
    return [
        name
        for name, (feat, pred) in _HARD_SPECS.items()
        if name in enabled and pred(features.get(feat))
    ]


def soft_score(features: dict) -> float:
    """Skor risiko kontinu (formula tertimbang, clamp ke [0,1])."""
    total = sum(w * features.get(feat, 0.0) for feat, _label, w in SOFT_FACTORS)
    return min(1.0, total)


def evaluate_rules(features: dict, params: dict | None = None) -> RuleResult:
    enabled = enabled_hard_rules(params)
    triggered = _hard_triggers(features, enabled)
    rules_risk = soft_score(features)
    return RuleResult(hard_block=bool(triggered), triggered=triggered, rules_risk=rules_risk)
