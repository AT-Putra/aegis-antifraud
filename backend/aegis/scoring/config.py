"""Konfigurasi scoring aktif (dari rule_configs). Diinjeksikan ke engine (decoupling)."""

from __future__ import annotations

from dataclasses import dataclass

from aegis.db.oltp import rule_configs_repo
from aegis.db.postgres import connection


@dataclass
class ScoringConfig:
    version: int
    threshold: float
    blend_weights: dict
    params: dict
    model_version: int | None = None


def load_active_config() -> ScoringConfig:
    with connection() as conn:
        row = rule_configs_repo.get_active(conn)
    if row is None:
        raise RuntimeError("tidak ada rule_config aktif")
    return ScoringConfig(
        version=row["version"],
        threshold=float(row["threshold"]),
        blend_weights=row["blend_weights"] or {},
        params=row["params"] or {},
    )
