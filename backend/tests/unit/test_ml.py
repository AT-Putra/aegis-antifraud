"""AC-ML-01: train→save→load→predict; kalibrasi [0,1]; cold-start fallback; determinisme."""

import numpy as np

from aegis.features.schema import FEATURE_ORDER, FEATURE_VERSION
from aegis.ml.inference import ScoringModels
from aegis.ml.isolation_forest import IsolationForestModel
from aegis.ml.store import save_artifact
from aegis.ml.train import train_models

_DIM = len(FEATURE_ORDER)


def _dataset(n: int = 60):
    rng = np.random.default_rng(0)
    human = rng.normal(0.0, 0.1, size=(n, _DIM))
    bot = rng.normal(0.0, 0.1, size=(n, _DIM)) + 0.8
    X = np.vstack([human, bot])
    y = np.array([0] * n + [1] * n)
    return X, y


def test_train_save_load_predict(tmp_path) -> None:
    X, y = _dataset()
    res = train_models(X, y)
    assert res.lgbm is not None  # label cukup → LGBM dilatih
    assert res.feature_version == FEATURE_VERSION

    iso_path = tmp_path / "iso.pkl"
    lgbm_path = tmp_path / "lgbm.pkl"
    save_artifact(res.iso, iso_path)
    save_artifact(res.lgbm, lgbm_path)

    models = ScoringModels.load(
        iso_path=iso_path, lgbm_path=lgbm_path, feature_version=res.feature_version
    )
    sample = list(X[-1])  # bot-like
    scores = models.predict(sample)
    assert 0.0 <= scores.if_score <= 1.0
    assert 0.0 <= scores.lgbm_score <= 1.0


def test_cold_start_no_labels_if_only() -> None:
    X, _ = _dataset()
    res = train_models(X, y=None)  # tanpa label → cold-start
    assert res.lgbm is None
    assert res.metrics["lgbm_trained"] is False

    models = ScoringModels(iso=res.iso, lgbm=None)
    scores = models.predict(list(X[0]))
    assert scores.if_score is not None and 0.0 <= scores.if_score <= 1.0
    assert scores.lgbm_score is None  # fallback: tak crash


def test_isolation_forest_deterministic() -> None:
    X, _ = _dataset()
    a = IsolationForestModel.fit(X, random_state=42).anomaly_score(X[:5])
    b = IsolationForestModel.fit(X, random_state=42).anomaly_score(X[:5])
    assert a == b  # random_state tetap → reproducible


def test_anomaly_score_bounds_and_direction() -> None:
    X, y = _dataset()
    iso = IsolationForestModel.fit(X, random_state=42)
    scores = iso.anomaly_score(X)
    assert all(0.0 <= s <= 1.0 for s in scores)
