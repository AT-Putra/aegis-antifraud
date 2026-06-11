"""Inference: muat model aktif dari store & hasilkan skor per-model.

Fallback cold-start (ADR-005/008): bila artefak LGBM belum ada → `lgbm_score=None`,
tetap jalan dengan IF saja. Blend/threshold final = T-11 (scoring orchestrator).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aegis.ml.store import load_artifact


@dataclass
class ModelScores:
    if_score: float | None
    lgbm_score: float | None


class ScoringModels:
    def __init__(self, iso=None, lgbm=None, feature_version: str | None = None) -> None:
        self.iso = iso
        self.lgbm = lgbm
        self.feature_version = feature_version

    @classmethod
    def load(
        cls,
        *,
        iso_path: str | Path | None = None,
        lgbm_path: str | Path | None = None,
        feature_version: str | None = None,
    ) -> ScoringModels:
        iso = load_artifact(iso_path) if iso_path and Path(iso_path).exists() else None
        lgbm = load_artifact(lgbm_path) if lgbm_path and Path(lgbm_path).exists() else None
        return cls(iso=iso, lgbm=lgbm, feature_version=feature_version)

    def predict(self, vector: list[float]) -> ModelScores:
        x = [vector]
        if_score = self.iso.anomaly_score(x)[0] if self.iso is not None else None
        lgbm_score = self.lgbm.predict_proba(x)[0] if self.lgbm is not None else None
        return ModelScores(if_score=if_score, lgbm_score=lgbm_score)
