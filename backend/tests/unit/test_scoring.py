"""AC-SCORE-01/02: keputusan, hard-override, fail-safe, versioning."""

from aegis.features.schema import FeatureInput
from aegis.ml.inference import ModelScores
from aegis.schemas.scoring import Signals
from aegis.scoring.config import ScoringConfig
from aegis.scoring.engine import score


class StubModels:
    def __init__(self, if_score, lgbm_score):
        self._s = ModelScores(if_score=if_score, lgbm_score=lgbm_score)

    def predict(self, vector):
        return self._s


class RaisingModels:
    def predict(self, vector):
        raise RuntimeError("model down")


_CONFIG = ScoringConfig(
    version=1,
    threshold=0.5,
    blend_weights={"rules": 0.34, "isolation_forest": 0.33, "lightgbm": 0.33},
    params={},
    model_version=2,
)

_HUMAN = {
    "fingerprint": {
        "canvas_hash": "c1",
        "webgl": {"renderer": "Mali"},
        "browser_environment": {"is_webview": False},
    },
    "behavior": {
        "mouse": {"move_count": 120, "velocity_mean": 1.2},
        "touch": {"tap_count": 3},
        "timing": {"interaction_count": 8},
    },
    "automation_hints": {"webdriver": False},
    "integrity": {"ever_visible": True},
}
_BOT_HARD = {
    "fingerprint": {"canvas_hash": "c1", "browser_environment": {"is_webview": True}},
    "behavior": {"mouse": {"move_count": 0}},
    "automation_hints": {"webdriver": True},
}
_BOT_SOFT = {
    "fingerprint": {"canvas_hash": "c1", "browser_environment": {"is_webview": False}},
    "behavior": {"mouse": {"move_count": 0}},
    "automation_hints": {"webdriver": False},
}


def _fi(sig: dict) -> FeatureInput:
    return FeatureInput(signals=Signals(**sig))


def test_human_allow() -> None:
    out = score(_fi(_HUMAN), config=_CONFIG, models=StubModels(0.1, 0.1))
    assert out.decision == "allow"
    assert out.final_score < 0.5
    assert out.score_breakdown["isolation_forest"] == 0.1


def test_bot_high_model_block() -> None:
    out = score(_fi(_BOT_SOFT), config=_CONFIG, models=StubModels(0.95, 0.95))
    assert out.decision == "block"
    assert out.final_score >= 0.5


def test_hard_override_blocks_before_model() -> None:
    out = score(_fi(_BOT_HARD), config=_CONFIG, models=StubModels(0.0, 0.0))
    assert out.decision == "block"
    assert out.reason.startswith("rule:")
    assert out.score_breakdown["isolation_forest"] is None  # model tak dipanggil


def test_failsafe_model_error_rules_only() -> None:
    out = score(_fi(_HUMAN), config=_CONFIG, models=RaisingModels())
    assert out.reason == "failsafe:model_error_rules_only"
    assert out.decision == "allow"  # rules_risk rendah → allow


def test_records_versions_and_breakdown() -> None:
    out = score(_fi(_HUMAN), config=_CONFIG, models=StubModels(0.2, 0.2))
    assert out.rules_version == 1 and out.model_version == 2
    assert out.feature_version
    assert set(out.score_breakdown) == {"rules", "isolation_forest", "lightgbm"}
