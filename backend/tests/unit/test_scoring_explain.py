"""Penjelasan scoring audit-grade (03 §7): explain_rules/explain_blend/build_*.

Murni (tanpa DB). Memverifikasi tabel kontribusi faktor & komposisi final_score TIDAK
melenceng dari rules.py/blend.py: skor formula, hard-rule paksa, normalisasi bobot,
fallback rata-rata. Sumber tunggal bobot = SOFT_FACTORS.
"""

from __future__ import annotations

from aegis.scoring.blend import blend
from aegis.scoring.explain import (
    build_decision_explainability,
    explain_blend,
    explain_rules,
)
from aegis.scoring.rules import evaluate_rules, soft_score


def test_soft_formula_score_half() -> None:
    """automation_score=1.0 (×0.2) + webview_risk=1.0 (×0.3) = 0.5, tanpa hard-rule."""
    exp = explain_rules({"automation_score": 1.0, "webview_risk": 1.0})
    assert exp["applied_mode"] == "weighted_formula"
    assert exp["soft_score"] == 0.5
    assert exp["effective_score"] == 0.5
    assert exp["hard_rules_triggered"] == []
    contrib = {f["name"]: f["contribution"] for f in exp["factors"]}
    assert contrib["automation_score"] == 0.2
    assert contrib["webview_risk"] == 0.3
    assert sum(f["contribution"] for f in exp["factors"]) == 0.5


def test_hard_block_forces_effective_one() -> None:
    """webdriver → hard-rule terpicu: effective_score=1.0; formula tetap utk konteks."""
    exp = explain_rules({"auto_webdriver": 1.0, "automation_score": 1.0})
    assert exp["applied_mode"] == "hard_rule"
    assert "webdriver" in exp["hard_rules_triggered"]
    assert exp["effective_score"] == 1.0
    # Skor formula (soft) tetap dilaporkan: 0.2*1.0 = 0.2
    assert exp["soft_score"] == 0.2


def test_allow_all_zero() -> None:
    exp = explain_rules({})
    assert exp["soft_score"] == 0.0
    assert exp["effective_score"] == 0.0
    assert exp["hard_rules_triggered"] == []


def test_blend_normalization_matches_blend_py() -> None:
    """rules+IF tersedia, LGBM null → normalized weight & kontribusi == blend()."""
    breakdown = {"rules": 0.4, "isolation_forest": 0.8, "lightgbm": None}
    weights = {"rules": 1.0, "isolation_forest": 1.0, "lightgbm": 1.0}
    expected_final = blend(0.4, 0.8, None, weights)
    exp = explain_blend(
        breakdown, weights, final_score=expected_final,
        threshold=0.5, decision="block", reason=None,
    )
    assert exp["mode"] == "weighted_normalized"
    comps = {c["name"]: c for c in exp["components"]}
    assert comps["rules"]["normalized_weight"] == 0.5
    assert comps["isolation_forest"]["normalized_weight"] == 0.5
    assert comps["lightgbm"]["applied"] is False
    # Σ kontribusi komponen applied == final_score blend()
    total = sum(c["contribution"] for c in exp["components"] if c["applied"])
    assert abs(total - expected_final) < 1e-9


def test_zero_weight_simple_average_fallback() -> None:
    """Bobot 0 → fallback rata-rata sederhana (cold-start aman, cermin blend())."""
    breakdown = {"rules": 0.4, "isolation_forest": 0.8, "lightgbm": None}
    exp = explain_blend(
        breakdown, {}, final_score=blend(0.4, 0.8, None, {}),
        threshold=0.5, decision="block", reason=None,
    )
    assert exp["mode"] == "simple_average_fallback"
    comps = {c["name"]: c for c in exp["components"]}
    assert comps["rules"]["normalized_weight"] == 0.5
    assert comps["isolation_forest"]["normalized_weight"] == 0.5


def test_hard_rule_forced_blend_mode() -> None:
    """reason 'rule:*' → mode hard_rule_forced; komponen tak applied (blend tak dipakai)."""
    breakdown = {"rules": 0.2, "isolation_forest": 0.1, "lightgbm": None}
    exp = explain_blend(
        breakdown, {"rules": 1.0}, final_score=1.0,
        threshold=0.5, decision="block", reason="rule:webdriver",
    )
    assert exp["mode"] == "hard_rule_forced"
    assert all(not c["applied"] for c in exp["components"])


def test_rules_only_failsafe_mode() -> None:
    breakdown = {"rules": 0.7, "isolation_forest": None, "lightgbm": None}
    exp = explain_blend(
        breakdown, {"rules": 1.0}, final_score=0.7,
        threshold=0.5, decision="block", reason="failsafe:model_error_rules_only",
    )
    assert exp["mode"] == "rules_only_failsafe"
    assert all(not c["applied"] for c in exp["components"])


def test_build_full_object_shape() -> None:
    obj = build_decision_explainability(
        {"automation_score": 1.0, "webview_risk": 1.0},
        params={},
        score_breakdown={"rules": 0.5, "isolation_forest": 0.3, "lightgbm": None},
        blend_weights={"rules": 1.0, "isolation_forest": 1.0},
        final_score=0.4, threshold=0.5, decision="allow", reason=None,
        feature_source="stored_features", rules_version_used=1,
    )
    assert obj["available"] is True
    assert obj["feature_source"] == "stored_features"
    assert obj["rules_version_used"] == 1
    assert obj["models"]["attribution_available"] is False
    assert "rules" in obj and "blend" in obj and obj["rationale"]


# --- Operator seluler ID: NETRAL sejak ADR-024 (dulu pengurang -0.05) ---


def test_mobile_carrier_is_neutral() -> None:
    # ADR-024: fraud kini rutin pakai koneksi operator → diskon dicabut. Bobot 0 → skor
    # TAK berubah dgn/tanpa flag operator (tetap dicatat sbg fitur, hanya netral).
    assert soft_score({"no_behavior": 1.0}) == 0.2
    assert soft_score({"no_behavior": 1.0, "ip_is_mobile_carrier": 1.0}) == 0.2
    assert soft_score({"ip_is_mobile_carrier": 1.0}) == 0.0


def test_mobile_carrier_does_not_rescue_hard_block() -> None:
    # Bot ber-automasi di IP seluler tetap hard-block (pengaman).
    rr = evaluate_rules({"auto_webdriver": 1.0, "ip_is_mobile_carrier": 1.0})
    assert rr.hard_block is True
    assert "webdriver" in rr.triggered


def test_mobile_carrier_factor_in_explain() -> None:
    # Faktor tetap muncul di explainability (audit) tapi kontribusi 0.
    exp = explain_rules({"no_behavior": 1.0, "ip_is_mobile_carrier": 1.0})
    contrib = {f["name"]: f["contribution"] for f in exp["factors"]}
    assert contrib["ip_is_mobile_carrier"] == 0.0
    assert abs(exp["soft_score"] - 0.2) < 1e-9
