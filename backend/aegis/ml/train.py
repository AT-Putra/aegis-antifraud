"""Antarmuka training (dipakai pipeline retraining T-17).

Cold-start: Isolation Forest dulu; LGBM dilatih bila label tiap kelas >= ambang.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from aegis.features.schema import FEATURE_VERSION
from aegis.ml.isolation_forest import IsolationForestModel
from aegis.ml.lightgbm_model import LightGBMModel

_MIN_LABELS_PER_CLASS = 20  # ambang cold-start untuk melatih LGBM


@dataclass
class TrainResult:
    iso: IsolationForestModel
    lgbm: LightGBMModel | None
    feature_version: str
    metrics: dict


def train_models(X, y=None, *, random_state: int = 42) -> TrainResult:
    X = np.asarray(X, dtype=float)
    iso = IsolationForestModel.fit(X, random_state=random_state)

    lgbm: LightGBMModel | None = None
    metrics: dict = {"n_samples": int(len(X)), "lgbm_trained": False}

    if y is not None:
        y = np.asarray(y)
        pos = int((y == 1).sum())
        neg = int((y == 0).sum())
        if pos >= _MIN_LABELS_PER_CLASS and neg >= _MIN_LABELS_PER_CLASS:
            spw = neg / pos if pos else None
            lgbm = LightGBMModel.fit(X, y, random_state=random_state, scale_pos_weight=spw)
            metrics.update(lgbm_trained=True, scale_pos_weight=spw, pos=pos, neg=neg)

    return TrainResult(iso=iso, lgbm=lgbm, feature_version=FEATURE_VERSION, metrics=metrics)
