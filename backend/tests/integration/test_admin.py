"""AC-ADMIN-01..03 (`03 §6`): config versioned+rollback, model/user/service mgmt, role gate.

Di-skip bila PostgreSQL tak terjangkau. User auth dibuat langsung di DB; token di-mint via
create_token (sub=username) — username harus ada di DB (current_admin resolve via users_repo).
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
from aegis.security.jwt_auth import create_token
from aegis.security.passwords import hash_password

_PW = "s3cret-pass-123"


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


def _mk_user(role: str) -> str:
    username = f"{role}-{uuid.uuid4().hex[:10]}"
    with connection() as conn:
        users_repo.insert_user(
            conn, username=username, password_hash=hash_password(_PW), role=role
        )
    return username


@pytest.fixture
def admin_hdr() -> dict:
    return {"Authorization": f"Bearer {create_token(_mk_user('admin'), 'admin')}"}


@pytest.fixture
def user_hdr() -> dict:
    return {"Authorization": f"Bearer {create_token(_mk_user('user'), 'user')}"}


# --- AC-ADMIN-03: role enforcement ---
def test_role_enforcement(client, user_hdr) -> None:
    assert client.get("/v1/admin/users").status_code == 401  # tanpa token
    assert client.get("/v1/admin/users", headers=user_hdr).status_code == 403  # role user


def test_stale_admin_token_uses_current_db_role_and_active(client) -> None:
    username = _mk_user("admin")
    hdr = {"Authorization": f"Bearer {create_token(username, 'admin')}"}
    assert client.get("/v1/admin/users", headers=hdr).status_code == 200

    with connection() as conn:
        user = users_repo.get_by_username(conn, username)
        users_repo.update_user(conn, str(user["id"]), role="user")
    assert client.get("/v1/admin/users", headers=hdr).status_code == 403

    with connection() as conn:
        user = users_repo.get_by_username(conn, username)
        users_repo.update_user(conn, str(user["id"]), role="admin", active=False)
    assert client.get("/v1/admin/users", headers=hdr).status_code == 401
    assert client.get("/v1/users/me", headers=hdr).status_code == 401


# --- Auth ---
def test_login(client) -> None:
    username = _mk_user("admin")
    ok = client.post("/v1/auth/login", json={"username": username, "password": _PW})
    assert ok.status_code == 200 and ok.json()["role"] == "admin" and ok.json()["jwt"]
    bad = client.post("/v1/auth/login", json={"username": username, "password": "wrong"})
    assert bad.status_code == 401


def test_users_me(client, admin_hdr) -> None:
    me = client.get("/v1/users/me", headers=admin_hdr).json()
    assert me["role"] == "admin" and "timezone" in me
    upd = client.put("/v1/users/me", headers=admin_hdr, json={"timezone": "Asia/Makassar"})
    assert upd.json()["timezone"] == "Asia/Makassar"


# --- AC-ADMIN-01: config versioned + rollback ---
def test_config_versioned_and_rollback(client, admin_hdr) -> None:
    v1 = client.put("/v1/admin/config", headers=admin_hdr, json={
        "params": {"a": 1}, "threshold": 0.4, "blend_weights": {"rules": 1.0},
    }).json()["version"]
    cfg = client.get("/v1/admin/config", headers=admin_hdr).json()
    assert cfg["version"] == v1 and cfg["threshold"] == 0.4

    v2 = client.put("/v1/admin/config", headers=admin_hdr, json={
        "params": {"a": 2}, "threshold": 0.7, "blend_weights": {"rules": 1.0},
    }).json()["version"]
    assert v2 > v1
    assert client.get("/v1/admin/config", headers=admin_hdr).json()["threshold"] == 0.7

    versions = client.get("/v1/admin/config/versions", headers=admin_hdr).json()
    by_ver = {r["version"]: r for r in versions}
    assert by_ver[v2]["active"] is True and by_ver[v1]["active"] is False

    # GET /admin/config/{version} → ambil params versi lama (untuk rollback satu-klik)
    old = client.get(f"/v1/admin/config/{v1}", headers=admin_hdr).json()
    assert old["params"] == {"a": 1} and old["threshold"] == 0.4 and old["active"] is False
    assert client.get("/v1/admin/config/999999", headers=admin_hdr).status_code == 404

    # rollback = PUT params versi lama → versi baru aktif dengan threshold lama
    v3 = client.put("/v1/admin/config", headers=admin_hdr, json={
        "params": {"a": 1}, "threshold": 0.4, "blend_weights": {"rules": 1.0},
    }).json()["version"]
    assert v3 > v2
    assert client.get("/v1/admin/config", headers=admin_hdr).json()["threshold"] == 0.4


# --- AC-ADMIN-02: users ---
def test_users_crud(client, admin_hdr) -> None:
    uname = f"new-{uuid.uuid4().hex[:10]}"
    r = client.post("/v1/admin/users", headers=admin_hdr,
                    json={"username": uname, "password": _PW, "role": "user"})
    uid = r.json()["id"]
    dup = client.post("/v1/admin/users", headers=admin_hdr,
                      json={"username": uname, "password": _PW, "role": "user"})
    assert dup.status_code == 409
    upd = client.put(f"/v1/admin/users/{uid}", headers=admin_hdr,
                     json={"role": "admin", "active": False}).json()
    assert upd["role"] == "admin" and upd["active"] is False
    assert uid in {u["id"] for u in client.get("/v1/admin/users", headers=admin_hdr).json()}


# --- AC-ADMIN-02: services (secret write-only) ---
def test_services_crud_secret_writeonly(client, admin_hdr) -> None:
    slug = f"svc-{uuid.uuid4().hex[:10]}"
    r = client.post("/v1/admin/services", headers=admin_hdr, json={
        "slug": slug, "name": "Svc", "operator": "OpX",
        "cp_api_url": "https://cp.example/req", "hmac_secret": "topsecret123",
    })
    sid = r.json()["id"]
    listing = client.get("/v1/admin/services", headers=admin_hdr).json()
    item = next(s for s in listing if s["id"] == sid)
    assert "hmac_secret" not in item and item["slug"] == slug
    upd = client.put(f"/v1/admin/services/{sid}", headers=admin_hdr,
                     json={"name": "Renamed", "status": "inactive"}).json()
    assert upd["name"] == "Renamed" and upd["status"] == "inactive"
    assert "hmac_secret" not in upd


# --- AC-ADMIN-02: models & retrain (aktivasi = approval) ---
def _insert_model(version: int, algorithm: str) -> str:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO model_versions (version, algorithm, metrics) "
            "VALUES (%s, %s, '{}'::jsonb) RETURNING id",
            (version, algorithm),
        )
        return str(cur.fetchone()[0])


def test_models_activate_and_retrain(client, admin_hdr) -> None:
    base = 900000 + uuid.uuid4().int % 50000
    m1 = _insert_model(base, "lightgbm")
    m2 = _insert_model(base + 1, "lightgbm")
    ids = {m["id"]: m for m in client.get("/v1/admin/models", headers=admin_hdr).json()}
    assert m1 in ids and m2 in ids

    a1 = client.post(f"/v1/admin/models/{m1}/activate", headers=admin_hdr).json()
    assert a1["active"] is True
    a2 = client.post(f"/v1/admin/models/{m2}/activate", headers=admin_hdr).json()
    assert a2["active"] is True
    # m1 harus non-aktif setelah m2 diaktifkan (hanya satu aktif)
    after = {m["id"]: m for m in client.get("/v1/admin/models", headers=admin_hdr).json()}
    assert after[m1]["active"] is False

    assert client.post("/v1/admin/models/" + str(uuid.uuid4()) + "/activate",
                       headers=admin_hdr).status_code == 404

    job = client.post("/v1/admin/retrain", headers=admin_hdr).json()
    assert job["status"] == "queued" and job["job_id"]
    got = client.get(f"/v1/admin/retrain/{job['job_id']}", headers=admin_hdr).json()
    assert got["status"] == "queued"


# --- Feedback (user submit → admin review) ---
def test_feedback_flow(client, admin_hdr, user_hdr) -> None:
    fid = client.post("/v1/feedback", headers=user_hdr,
                      json={"flagged_label": "robot", "note": "uji"}).json()["id"]
    pending = client.get("/v1/admin/feedback", headers=admin_hdr,
                         params={"status": "pending"}).json()
    assert fid in {f["id"] for f in pending}
    rev = client.put(f"/v1/admin/feedback/{fid}/review", headers=admin_hdr,
                     json={"review_status": "accepted"}).json()
    assert rev["review_status"] == "accepted"


# --- Settings ---
def test_settings(client, admin_hdr) -> None:
    seeded = client.get("/v1/admin/settings", headers=admin_hdr).json()
    assert any(s["key"] == "default_timezone" for s in seeded)
    key = f"k-{uuid.uuid4().hex[:8]}"
    upd = client.put("/v1/admin/settings", headers=admin_hdr,
                     json={"key": key, "value": "v1"}).json()
    assert upd == {"key": key, "value": "v1"}
    again = client.get("/v1/admin/settings", headers=admin_hdr).json()
    assert {"key": key, "value": "v1"} in [{"key": s["key"], "value": s["value"]} for s in again]
