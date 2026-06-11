"""Blend skor 3-lapis (ADR-008). Normalisasi atas komponen tersedia → cold-start aman."""

from __future__ import annotations


def blend(
    rules_risk: float,
    if_score: float | None,
    lgbm_score: float | None,
    weights: dict | None,
) -> float:
    weights = weights or {}
    parts: list[tuple[float, float]] = [(float(weights.get("rules", 0.0)), rules_risk)]
    if if_score is not None:
        parts.append((float(weights.get("isolation_forest", 0.0)), if_score))
    if lgbm_score is not None:
        parts.append((float(weights.get("lightgbm", 0.0)), lgbm_score))

    total_w = sum(w for w, _ in parts)
    if total_w <= 0:
        vals = [v for _, v in parts]
        return min(1.0, sum(vals) / len(vals)) if vals else rules_risk
    return min(1.0, sum(w * v for w, v in parts) / total_w)
