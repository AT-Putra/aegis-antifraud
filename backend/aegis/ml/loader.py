"""Muat model aktif dari store saat startup. Cold-start (tak ada) → ScoringModels kosong."""

from __future__ import annotations

from pathlib import Path

from aegis.config import get_settings
from aegis.db.oltp import model_versions_repo
from aegis.db.postgres import connection
from aegis.ml.inference import ScoringModels


def load_active_models() -> tuple[ScoringModels, int | None]:
    """Konvensi path artefak: {MODEL_DIR}/v{version}/{iso,lgbm}.pkl (ditulis T-17)."""
    try:
        with connection() as conn:
            row = model_versions_repo.get_active(conn)
    except Exception:
        row = None
    if not row:
        return ScoringModels(iso=None, lgbm=None), None

    version = row["version"]
    base = Path(get_settings().model_dir) / f"v{version}"
    models = ScoringModels.load(
        iso_path=base / "iso.pkl",
        lgbm_path=base / "lgbm.pkl",
        feature_version=None,
    )
    return models, version
