"""Penjelasan keputusan scoring (audit-grade, murni — TANPA DB).

Memakai ulang `SOFT_FACTORS` & helper hard-rule dari `scoring/rules.py` dan perilaku
normalisasi dari `scoring/blend.py`, sehingga penjelasan tak pernah melenceng dari skor
sebenarnya. Tidak menghitung atribusi per-fitur model (SHAP) — belum tersedia (rilis-1).

`build_decision_explainability()` menyusun objek `explainability` sesuai kontrak 03 §7.
"""

from __future__ import annotations

from aegis.scoring.rules import (
    SOFT_FACTORS,
    _hard_triggers,
    enabled_hard_rules,
    soft_score,
)

EXPLAIN_VERSION = "1"

_RULES_FORMULA = (
    "rules_risk = max(0.0, min(1.0, "
    "0.2·automation_score + 0.3·webview_risk + 0.3·ip_is_datacenter "
    "+ 0.2·ip_is_vpn_proxy_tor + 0.2·no_behavior "
    "+ 0.3·fp_claims_desktop_but_mobile + 0.3·os_hw_family_mismatch "
    "+ 0.2·low_fp_entropy))"
)

_COMPONENT_WEIGHT_KEY = {
    "rules": "rules",
    "isolation_forest": "isolation_forest",
    "lightgbm": "lightgbm",
}
_COMPONENT_LABEL = {
    "rules": "Rules",
    "isolation_forest": "Isolation Forest",
    "lightgbm": "LightGBM",
}


def explain_rules(features: dict, params: dict | None = None) -> dict:
    """Rincian skor rules: tabel kontribusi faktor + status hard-rule.

    `effective_score` = skor rules yang BENAR-benar dipakai keputusan: 1.0 saat hard-rule
    terpicu (block paksa), selain itu = skor formula. Formula tetap ditampilkan utk konteks.
    """
    enabled = enabled_hard_rules(params)
    triggered = _hard_triggers(features, enabled)

    factors = []
    soft_sum = 0.0
    for feat, label, weight in SOFT_FACTORS:
        value = float(features.get(feat, 0.0) or 0.0)
        contribution = value * weight
        soft_sum += contribution
        factors.append(
            {
                "name": feat,
                "label": label,
                "value": value,
                "weight": weight,
                "contribution": contribution,
            }
        )

    soft = soft_score(features)  # = min(1.0, soft_sum) — sumber tunggal
    applied_mode = "hard_rule" if triggered else "weighted_formula"
    effective = 1.0 if triggered else soft

    return {
        "formula": _RULES_FORMULA,
        "applied_mode": applied_mode,
        "soft_sum": soft_sum,
        "soft_score": soft,
        "effective_score": effective,
        "hard_rules_enabled": sorted(enabled),
        "hard_rules_triggered": triggered,
        "factors": factors,
    }


def explain_blend(
    score_breakdown: dict,
    blend_weights: dict | None,
    *,
    final_score: float | None,
    threshold: float,
    decision: str,
    reason: str | None,
) -> dict:
    """Komposisi `final_score` per-komponen (cermin perilaku `blend.py`).

    Hanya komponen dengan skor non-null yang `applied`. Mode:
    - hard_rule_forced  : reason "rule:*" → block paksa, blend tak dipakai.
    - rules_only_failsafe: reason "failsafe:*" → model gagal/absen, rules saja.
    - weighted_normalized / simple_average_fallback: jalur normal (total bobot >0 / =0).
    """
    weights = blend_weights or {}

    forced = bool(reason and reason.startswith("rule:"))
    failsafe = bool(reason and reason.startswith("failsafe:"))

    # Komponen yang tersedia (skor non-null) → ikut normalisasi seperti blend().
    available: list[tuple[str, float, float]] = []  # (name, score, weight)
    for name in ("rules", "isolation_forest", "lightgbm"):
        raw = score_breakdown.get(name)
        if raw is None:
            continue
        w = float(weights.get(_COMPONENT_WEIGHT_KEY[name], 0.0))
        available.append((name, float(raw), w))

    total_w = sum(w for _n, _s, w in available)
    use_fallback = total_w <= 0

    if forced:
        mode = "hard_rule_forced"
    elif failsafe:
        mode = "rules_only_failsafe"
    elif use_fallback:
        mode = "simple_average_fallback"
    else:
        mode = "weighted_normalized"

    components = []
    for name in ("rules", "isolation_forest", "lightgbm"):
        raw = score_breakdown.get(name)
        w = float(weights.get(_COMPONENT_WEIGHT_KEY[name], 0.0))
        if raw is None:
            components.append(
                {
                    "name": name,
                    "label": _COMPONENT_LABEL[name],
                    "score": None,
                    "weight": w,
                    "normalized_weight": 0.0,
                    "contribution": 0.0,
                    "applied": False,
                }
            )
            continue
        score_val = float(raw)
        # Pada mode paksa/failsafe blend tak menentukan final → komponen ditandai tak applied.
        if forced or failsafe:
            norm_w = 0.0
            contribution = 0.0
            applied = False
        elif use_fallback:
            norm_w = 1.0 / len(available) if available else 0.0
            contribution = score_val * norm_w
            applied = True
        else:
            norm_w = w / total_w if total_w > 0 else 0.0
            contribution = score_val * norm_w
            applied = norm_w > 0
        components.append(
            {
                "name": name,
                "label": _COMPONENT_LABEL[name],
                "score": score_val,
                "weight": w,
                "normalized_weight": norm_w,
                "contribution": contribution,
                "applied": applied,
            }
        )

    return {
        "final_score": final_score,
        "threshold": threshold,
        "decision": decision,
        "reason": reason,
        "mode": mode,
        "components": components,
    }


def _rationale(rules_exp: dict, blend_exp: dict) -> str:
    decision = blend_exp["decision"]
    final = blend_exp["final_score"]
    threshold = blend_exp["threshold"]
    final_txt = f"{final:.3f}" if isinstance(final, (int, float)) else "—"
    if rules_exp["applied_mode"] == "hard_rule":
        trg = ", ".join(rules_exp["hard_rules_triggered"])
        return f"Diblokir oleh hard-rule ({trg}); skor model diabaikan."
    if blend_exp["mode"] == "rules_only_failsafe":
        verb = "diblokir" if decision == "block" else "diloloskan"
        return (
            f"Model gagal/absen → fail-safe rules-only: skor {final_txt} "
            f"{'≥' if decision == 'block' else '<'} ambang {threshold} → {verb}."
        )
    verb = "diblokir" if decision == "block" else "diloloskan"
    cmp = "≥" if decision == "block" else "<"
    return f"Skor akhir {final_txt} {cmp} ambang {threshold} → {verb}."


def build_decision_explainability(
    features: dict,
    *,
    params: dict | None,
    score_breakdown: dict,
    blend_weights: dict | None,
    final_score: float | None,
    threshold: float,
    decision: str,
    reason: str | None,
    feature_source: str,
    rules_version_used: int | None,
    warnings: list[str] | None = None,
) -> dict:
    """Susun objek `explainability` lengkap (03 §7). Murni — tanpa DB."""
    rules_exp = explain_rules(features, params)
    blend_exp = explain_blend(
        score_breakdown,
        blend_weights,
        final_score=final_score,
        threshold=threshold,
        decision=decision,
        reason=reason,
    )
    return {
        "available": True,
        "version": EXPLAIN_VERSION,
        "feature_source": feature_source,
        "warnings": warnings or [],
        "rules_version_used": rules_version_used,
        "rules": rules_exp,
        "blend": blend_exp,
        "models": {
            "attribution_available": False,
            "note": (
                "Skor IF/LightGBM ditampilkan sebagai skalar × bobot blend. "
                "Atribusi per-fitur (SHAP) belum tersedia di rilis-1."
            ),
        },
        "rationale": _rationale(rules_exp, blend_exp),
    }
