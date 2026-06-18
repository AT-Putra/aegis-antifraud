"""Unit: normalisasi & validasi kode negara geo-allowlist (F-17)."""

from __future__ import annotations

import pytest

from aegis.registry.countries import ISO_3166_1_ALPHA2, normalize_countries


def test_empty_is_all() -> None:
    assert normalize_countries([]) == []


def test_uppercase_and_dedupe_preserves_order() -> None:
    assert normalize_countries(["id", "ID", " my ", "MY", "us"]) == ["ID", "MY", "US"]


def test_invalid_code_raises() -> None:
    with pytest.raises(ValueError):
        normalize_countries(["ID", "ZZ"])


def test_known_codes_present() -> None:
    assert {"ID", "MY", "US", "SG"} <= ISO_3166_1_ALPHA2
