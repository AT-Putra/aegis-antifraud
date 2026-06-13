"""Endpoint registry read-only untuk dropdown filter dashboard (03 §7).

`GET /v1/registry/services` & `GET /v1/registry/campaigns?service` — admin & user (read-only),
hanya field non-sensitif {slug, name, status}; campaign chaining via `?service`.
Di-skip bila PostgreSQL tak terjangkau (pola integrasi repo).
"""

from __future__ import annotations

import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from aegis.config import get_settings
from aegis.db.migrate import migrate_oltp
from aegis.db.oltp import users_repo
from aegis.db.postgres import connection
from aegis.registry.service import register_service
from aegis.security.jwt_auth import create_token
from aegis.security.passwords import hash_password


def _reachable() -> bool:
    try:
        with psycopg.connect(get_settings().postgres_dsn, connect_timeout=3):
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _reachable(), reason="PostgreSQL tak terjangkau")


@pytest.fixture(scope="module", autouse=True)
def _migrated():
    migrate_oltp(get_settings())


@pytest.fixture
def client():
    from aegis.main import app

    with TestClient(app) as c:
        yield c


def _auth(role: str) -> dict:
    username = f"{role}-{uuid.uuid4().hex[:10]}"
    with connection() as conn:
        users_repo.insert_user(
            conn, username=username, password_hash=hash_password("x"), role=role
        )
    return {"Authorization": f"Bearer {create_token(username, role)}"}


def _service() -> str:
    slug = f"svc-{uuid.uuid4().hex[:10]}"
    register_service(slug, "Svc Name", "Telco", "https://cp.example/req", "secret")
    return slug


def _create_campaign(client, auth, service) -> str:
    slug = f"camp-{uuid.uuid4().hex[:10]}"
    r = client.post(
        "/v1/admin/campaigns",
        headers=auth,
        json={"slug": slug, "name": "Camp Name", "service": service, "allowed_origins": []},
    )
    assert r.status_code == 200, r.text
    return slug


def test_registry_services_shape_no_secret(client) -> None:
    admin = _auth("admin")
    svc = _service()
    rows = client.get("/v1/registry/services", headers=admin)
    assert rows.status_code == 200, rows.text
    data = rows.json()
    item = next(s for s in data if s["slug"] == svc)
    # hanya field non-sensitif
    assert set(item.keys()) == {"slug", "name", "status"}
    assert item["name"] == "Svc Name" and item["status"] == "active"


def test_registry_accessible_to_user_role(client) -> None:
    """Filter dipakai role user (read-only) — tak boleh 403 seperti /v1/admin/*."""
    user = _auth("user")
    assert client.get("/v1/registry/services", headers=user).status_code == 200
    assert client.get("/v1/registry/campaigns", headers=user).status_code == 200


def test_registry_campaigns_chained_by_service(client) -> None:
    admin = _auth("admin")
    svc_a = _service()
    svc_b = _service()
    camp_a = _create_campaign(client, admin, svc_a)
    camp_b = _create_campaign(client, admin, svc_b)

    only_a = client.get(
        "/v1/registry/campaigns", headers=admin, params={"service": svc_a}
    ).json()
    slugs_a = {c["slug"] for c in only_a}
    assert camp_a in slugs_a
    assert camp_b not in slugs_a  # chaining: campaign service lain tak muncul


def test_registry_requires_auth(client) -> None:
    # Tanpa header Authorization → 401 (app menormalkan ke unauthorized).
    assert client.get("/v1/registry/services").status_code == 401
