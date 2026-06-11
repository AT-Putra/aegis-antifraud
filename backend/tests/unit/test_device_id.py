"""AC-FP-01.1: device_id deterministik & kanonikal stabil (ADR-004)."""

from aegis.fingerprint.device_id import compute_device_id
from aegis.schemas.scoring import Fingerprint

_BASE = {
    "canvas_hash": "c1",
    "audio_hash": "a1",
    "webgl": {"vendor": "Acme", "renderer": "GPU-X"},
    "screen": {"width": 412, "height": 915, "colorDepth": 24, "devicePixelRatio": 2.625},
    "fonts": ["Arial", "Roboto", "Times"],
    "timezone": "Asia/Jakarta",
    "languages": ["id-ID", "en-US"],
    "hardwareConcurrency": 8,
    "deviceMemory": 4,
    "platform": "Linux armv8l",
}


def _fp(**override) -> Fingerprint:
    return Fingerprint(**{**_BASE, **override})


def test_same_signals_same_id() -> None:
    assert compute_device_id(_fp()) == compute_device_id(_fp())


def test_changed_component_changes_id() -> None:
    assert compute_device_id(_fp()) != compute_device_id(_fp(canvas_hash="c2"))


def test_fonts_order_irrelevant() -> None:
    a = compute_device_id(_fp(fonts=["Arial", "Roboto", "Times"]))
    b = compute_device_id(_fp(fonts=["Times", "Arial", "Roboto"]))
    assert a == b  # fonts di-sort → stabil


def test_languages_order_matters() -> None:
    a = compute_device_id(_fp(languages=["id-ID", "en-US"]))
    b = compute_device_id(_fp(languages=["en-US", "id-ID"]))
    assert a != b  # urutan languages bermakna


def test_id_is_sha256_hex() -> None:
    did = compute_device_id(_fp())
    assert len(did) == 64 and all(c in "0123456789abcdef" for c in did)
