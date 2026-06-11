"""Orkestrasi keputusan scoring dengan fail-safe berlapis (ADR-005, TRD §5/§6).

Decoupled: `config` & `models` diinjeksikan (di-load oleh api T-12). Engine murni.
Fail-safe: ekstraksi/rules gagal → block; model gagal → rules-only; hard-rule → block.
"""

from __future__ import annotations

from dataclasses import dataclass

from aegis.features.extract import extract_features, feature_vector
from aegis.features.schema import FEATURE_VERSION, FeatureInput
from aegis.scoring.blend import blend
from aegis.scoring.config import ScoringConfig
from aegis.scoring.rules import evaluate_rules


@dataclass
class ScoreOutcome:
    decision: str  # "allow" | "block"
    final_score: float
    threshold_used: float
    rules_version: int | None
    model_version: int | None
    feature_version: str
    reason: str | None
    score_breakdown: dict


def _outcome(
    decision: str, final: float, config: ScoringConfig, reason: str | None, breakdown: dict
) -> ScoreOutcome:
    return ScoreOutcome(
        decision=decision,
        final_score=final,
        threshold_used=config.threshold,
        rules_version=config.version,
        model_version=config.model_version,
        feature_version=FEATURE_VERSION,
        reason=reason,
        score_breakdown=breakdown,
    )


def score(feature_input: FeatureInput, *, config: ScoringConfig, models) -> ScoreOutcome:
    breakdown: dict = {"rules": None, "isolation_forest": None, "lightgbm": None}

    try:
        features = extract_features(feature_input)
        vector = feature_vector(features)
    except Exception:
        return _outcome("block", 1.0, config, "failsafe:extract_error", breakdown)

    try:
        rr = evaluate_rules(features, config.params)
    except Exception:
        return _outcome("block", 1.0, config, "failsafe:rules_error", breakdown)
    breakdown["rules"] = rr.rules_risk

    if rr.hard_block:
        return _outcome("block", 1.0, config, f"rule:{rr.triggered[0]}", breakdown)

    try:
        ms = models.predict(vector)
        if_score, lgbm_score = ms.if_score, ms.lgbm_score
    except Exception:
        final = rr.rules_risk
        decision = "block" if final >= config.threshold else "allow"
        return _outcome(decision, final, config, "failsafe:model_error_rules_only", breakdown)

    breakdown["isolation_forest"] = if_score
    breakdown["lightgbm"] = lgbm_score
    final = blend(rr.rules_risk, if_score, lgbm_score, config.blend_weights)
    decision = "block" if final >= config.threshold else "allow"
    return _outcome(decision, final, config, None, breakdown)
