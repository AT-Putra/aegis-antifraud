"""Wrapper LightGBM (supervised) + kalibrasi probabilitas (ADR-008). Kelas 1 = robot/fraud."""

from __future__ import annotations

import numpy as np
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV


class LightGBMModel:
    def __init__(self, model=None) -> None:
        self.model = model

    @classmethod
    def fit(
        cls,
        X,
        y,
        *,
        random_state: int = 42,
        scale_pos_weight: float | None = None,
        calibrate: bool = True,
        cv: int = 3,
    ) -> LightGBMModel:
        X = np.asarray(X, dtype=float)
        y = np.asarray(y)
        base = LGBMClassifier(
            random_state=random_state, scale_pos_weight=scale_pos_weight, verbose=-1
        )
        if calibrate:
            model = CalibratedClassifierCV(base, method="isotonic", cv=cv)
            model.fit(X, y)
        else:
            base.fit(X, y)
            model = base
        return cls(model)

    def predict_proba(self, X) -> list[float]:
        """Probabilitas terkalibrasi kelas 1 (robot)."""
        proba = self.model.predict_proba(np.asarray(X, dtype=float))[:, 1]
        return [float(p) for p in proba]
