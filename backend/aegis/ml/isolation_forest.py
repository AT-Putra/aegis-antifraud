"""Wrapper Isolation Forest (unsupervised, cold-start). Skor → [0,1], 1=anomali (K2)."""

from __future__ import annotations

import math

import numpy as np
from sklearn.ensemble import IsolationForest

# Faktor ketajaman sigmoid: decision_function IF kecil → perlu di-skala agar diskriminatif.
_SCALE = 8.0


class IsolationForestModel:
    def __init__(self, model: IsolationForest | None = None) -> None:
        self.model = model

    @classmethod
    def fit(cls, X, *, random_state: int = 42, contamination="auto") -> IsolationForestModel:
        clf = IsolationForest(random_state=random_state, contamination=contamination)
        clf.fit(np.asarray(X, dtype=float))
        return cls(clf)

    def anomaly_score(self, X) -> list[float]:
        """1 - sigmoid(k·decision_function): positif(normal)→rendah; negatif(anomali)→tinggi."""
        df = self.model.decision_function(np.asarray(X, dtype=float))
        return [1.0 - 1.0 / (1.0 + math.exp(-_SCALE * float(v))) for v in df]
