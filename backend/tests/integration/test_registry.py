"""AC-REG-01: registry CRUD, secret write-only/roundtrip, soft-delete, slug immutable."""

import uuid

import psycopg
import pytest

from aegis.config import get_settings
from aegis.registry.errors import ServiceExistsError
from aegis.registry.service import (
    get_active_service,
    get_service_secret,
    list_services,
    register_service,
    update_service,
)


def _reachable() -> bool:
    try:
        with psycopg.connect(get_settings().postgres_dsn, connect_timeout=3):
            return True
    except Exception:
        return False


def _slug() -> str:
    return f"svc-{uuid.uuid4().hex[:12]}"


def test_register_secret_roundtrip_and_active() -> None:
    if not _reachable():
        pytest.skip("PostgreSQL tak terjangkau")
    slug = _slug()
    out = register_service(slug, "Fun Zone", "TelcoX", "https://cp.example/req", "super-secret")
    assert out.slug == slug
    assert "hmac_secret" not in out.model_dump()  # DTO write-only
    assert get_service_secret(slug) == "super-secret"  # roundtrip enkripsi
    rt = get_active_service(slug)
    assert rt is not None and rt.cp_api_url == "https://cp.example/req"


def test_duplicate_slug() -> None:
    if not _reachable():
        pytest.skip("PostgreSQL tak terjangkau")
    slug = _slug()
    register_service(slug, "A", None, "https://a.example", "s1")
    with pytest.raises(ServiceExistsError):
        register_service(slug, "B", None, "https://b.example", "s2")


def test_invalid_slug_and_url() -> None:
    with pytest.raises(ValueError):
        register_service("BadSlug", "x", None, "https://a.example", "s")
    if not _reachable():
        pytest.skip("PostgreSQL tak terjangkau")
    with pytest.raises(ValueError):
        register_service(_slug(), "x", None, "http://insecure.example", "s")


def test_soft_delete_keeps_record() -> None:
    if not _reachable():
        pytest.skip("PostgreSQL tak terjangkau")
    slug = _slug()
    out = register_service(slug, "A", None, "https://a.example", "s")
    update_service(out.id, status="inactive")
    assert get_active_service(slug) is None
    assert slug in {s.slug for s in list_services()}  # masih ada


def test_slug_immutable() -> None:
    if not _reachable():
        pytest.skip("PostgreSQL tak terjangkau")
    slug = _slug()
    out = register_service(slug, "A", None, "https://a.example", "s")
    updated = update_service(out.id, name="B")
    assert updated.slug == slug and updated.name == "B"
