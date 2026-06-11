"""Rules engine (murni): hard-override + skor risiko kontinu. Default tuning = TQ-02."""

from __future__ import annotations

from dataclasses import dataclass

_DEFAULT_HARD_RULES = (
    "webdriver",
    "headless",
    "automation_globals",
    "isTrusted_false",
    "software_render",
)


@dataclass
class RuleResult:
    hard_block: bool
    triggered: list[str]
    rules_risk: float


def evaluate_rules(features: dict, params: dict | None = None) -> RuleResult:
    params = params or {}
    enabled = set(params.get("hard_rules", _DEFAULT_HARD_RULES))

    triggered: list[str] = []
    if "webdriver" in enabled and features.get("auto_webdriver"):
        triggered.append("webdriver")
    if "headless" in enabled and features.get("auto_headless"):
        triggered.append("headless")
    if "automation_globals" in enabled and features.get("auto_globals_count", 0) > 0:
        triggered.append("automation_globals")
    if "isTrusted_false" in enabled and features.get("auto_istrusted_false"):
        triggered.append("isTrusted_false")
    if "software_render" in enabled and features.get("auto_software_render"):
        triggered.append("software_render")

    rules_risk = min(
        1.0,
        0.2 * features.get("automation_score", 0.0)
        + 0.3 * features.get("webview_risk", 0.0)
        + 0.3 * features.get("ip_is_datacenter", 0.0)
        + 0.2 * features.get("ip_is_vpn_proxy_tor", 0.0)
        + 0.2 * features.get("no_behavior", 0.0),
    )
    return RuleResult(hard_block=bool(triggered), triggered=triggered, rules_risk=rules_risk)
