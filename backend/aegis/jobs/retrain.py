"""Pipeline retraining terjadwal (T-17, TRD §5 Alur 3, ADR-008).

Alur: kumpulkan label (OLTP decisions+outcomes) → maturation window + override feedback
admin → ambil fitur per-trx dari OLAP (skew-free) → train_models (IF selalu; LGBM bila
≥20/kelas) → simpan artefak MODEL_DIR/v{n} → daftar model_versions (active=false; aktivasi
= approval admin via `POST /v1/admin/models/{id}/activate`).

CLI: `python -m aegis.jobs.retrain [--job-id <uuid>]`
Catatan: model aktif dimuat saat startup → perlu restart api agar model baru efektif.
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime
from pathlib import Path

from aegis.config import get_settings
from aegis.db.olap import analytics_repo
from aegis.db.oltp import (
    model_versions_repo,
    retrain_jobs_repo,
    settings_repo,
    training_repo,
)
from aegis.db.postgres import connection
from aegis.features.extract import feature_vector
from aegis.ml import store
from aegis.ml.train import train_models
from aegis.scoring.config import load_active_config
from aegis.scoring.rules import evaluate_rules
from aegis.services import feedback as feedback_svc
from aegis.services.maturation import DEFAULT_MATURATION_DAYS, is_human_label

_log = logging.getLogger("aegis.retrain")

# Label model: kelas 1 = robot, kelas 0 = human (konsisten LightGBMModel T-06).
_HUMAN, _ROBOT = 0, 1


def _maturation_days() -> int:
    with connection() as conn:
        rows = settings_repo.list_all(conn)
    for r in rows:
        if r["key"] == "maturation_days":
            try:
                return int(r["value"])
            except (TypeError, ValueError):
                break
    return DEFAULT_MATURATION_DAYS


def _build_labels(maturation_days: int) -> dict[str, int]:
    """trx_id → label (0 human / 1 robot). Feedback admin menimpa label turunan."""
    now = datetime.now(UTC)
    labels: dict[str, int] = {}
    with connection() as conn:
        candidates = training_repo.labeled_candidates(conn)
    for c in candidates:
        ref = c["ref_time"]
        days = (now - ref).total_seconds() / 86400.0 if ref else 0.0
        verdict = is_human_label(
            subscription_success=bool(c["subscription_success"]),
            has_complaint=bool(c["has_complaint"]),
            days_elapsed=days,
            maturation_days=maturation_days,
            charging_fail_reason=c.get("charging_fail_reason"),
        )
        if verdict is True:
            labels[c["trx_id"]] = _HUMAN
        elif verdict is False:
            labels[c["trx_id"]] = _ROBOT
    # Override: ground truth admin (accepted feedback).
    for fb in feedback_svc.accepted_labels():
        if fb.get("trx_id"):
            labels[fb["trx_id"]] = _ROBOT if fb["flagged_label"] == "robot" else _HUMAN
    return labels


def _human_label_disqualified(feats: dict) -> bool:
    """Pengerasan label (ADR-020): charge sukses BUKAN bukti human bila scorer SENDIRI
    menandai trx berisiko (rules_risk ≥ threshold aktif ATAU hard-rule). Cegah poisoning."""
    try:
        cfg = load_active_config()
    except Exception:
        return False  # tanpa config aktif → tak bisa menilai → jangan buang label
    rr = evaluate_rules(feats, cfg.params)
    return rr.hard_block or rr.rules_risk >= cfg.threshold


def gather_training_data(maturation_days: int) -> tuple[list[list[float]], list[int], dict]:
    labels = _build_labels(maturation_days)
    features = analytics_repo.features_by_trx(list(labels))
    X: list[list[float]] = []
    y: list[int] = []
    excluded_poison = 0
    for trx, label in labels.items():
        feats = features.get(trx)
        if feats is None:  # fitur OLAP hilang (loss) → lewati
            continue
        if label == _HUMAN and _human_label_disqualified(feats):
            excluded_poison += 1  # charge sukses tapi berisiko → exclude (jangan latih sbg human)
            continue
        X.append(feature_vector(feats))
        y.append(label)
    meta = {
        "labeled_trx": len(labels),
        "with_features": len(X),
        "n_human": int(sum(1 for v in y if v == _HUMAN)),
        "n_robot": int(sum(1 for v in y if v == _ROBOT)),
        "excluded_poison": excluded_poison,
    }
    return X, y, meta


def run_retrain(job_id: str | None = None) -> dict:
    if job_id:
        with connection() as conn:
            retrain_jobs_repo.mark_running(conn, job_id)
    try:
        maturation_days = _maturation_days()
        X, y, meta = gather_training_data(maturation_days)
        if not X:
            result = {"status": "failed", "reason": "no_labeled_data", **meta}
            if job_id:
                with connection() as conn:
                    retrain_jobs_repo.mark_failed(conn, job_id, result)
            _log.warning("retrain dibatalkan: tak ada data berlabel berfitur")
            return result

        trained = train_models(X, y)
        with connection() as conn:
            version = model_versions_repo.next_version(conn)

        base = Path(get_settings().model_dir) / f"v{version}"
        store.save_artifact(trained.iso, base / "iso.pkl")
        calibration_ref = None
        if trained.lgbm is not None:
            store.save_artifact(trained.lgbm, base / "lgbm.pkl")
            calibration_ref = f"v{version}/lgbm.pkl"
        algorithm = "isolation_forest+lightgbm" if trained.lgbm else "isolation_forest"

        metrics = {**trained.metrics, **meta, "feature_version": trained.feature_version,
                   "maturation_days": maturation_days}
        with connection() as conn:
            row = model_versions_repo.insert_version(
                conn,
                version=version,
                algorithm=algorithm,
                artifact_ref=f"v{version}/iso.pkl",
                calibration_ref=calibration_ref,
                metrics=metrics,
            )
        result = {
            "status": "done",
            "model_id": str(row["id"]),
            "version": version,
            "algorithm": algorithm,
            "active": False,
            **metrics,
        }
        if job_id:
            with connection() as conn:
                retrain_jobs_repo.mark_done(conn, job_id, result)
        _log.info("retrain selesai: v%s (%s), active=false", version, algorithm)
        return result
    except Exception as exc:  # noqa: BLE001
        _log.exception("retrain gagal")
        if job_id:
            with connection() as conn:
                retrain_jobs_repo.mark_failed(conn, job_id, {"error": str(exc)})
        return {"status": "failed", "reason": str(exc)}


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Aegis retraining (T-17)")
    parser.add_argument("--job-id", dest="job_id", default=None)
    args = parser.parse_args()
    result = run_retrain(args.job_id)
    print(result)
    return 0 if result.get("status") == "done" else 1


if __name__ == "__main__":
    raise SystemExit(main())
