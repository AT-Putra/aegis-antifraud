"""Shared model store: serialisasi artefak model (joblib). ADR-003, K1."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib


def save_artifact(obj: Any, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(obj, p)


def load_artifact(path: str | Path) -> Any:
    return joblib.load(path)
