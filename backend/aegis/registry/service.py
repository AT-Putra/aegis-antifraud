"""Logika service registry: register/get/list/update + enkripsi secret (AES-GCM).

`hmac_secret` selalu disimpan ciphertext; plaintext hanya didekripsi server-side
untuk klien CP (T-08), tak pernah lewat API. Slug immutable; hapus = soft-delete.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import psycopg

from aegis.db.oltp import services_repo
from aegis.db.postgres import connection
from aegis.registry.errors import ServiceExistsError, ServiceNotFoundError
from aegis.schemas.admin import ServiceOut
from aegis.schemas.common import SLUG_PATTERN
from aegis.security.crypto import decrypt_secret, encrypt_secret


@dataclass
class ServiceRuntime:
    id: str
    slug: str
    cp_api_url: str
    status: str


def _to_out(row: dict) -> ServiceOut:
    return ServiceOut(
        id=row["id"],
        slug=row["slug"],
        name=row["name"],
        operator=row["operator"],
        cp_api_url=row["cp_api_url"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _require_https(url: str) -> None:
    if not url.startswith("https://"):
        raise ValueError("cp_api_url harus https")


def register_service(
    slug: str, name: str, operator: str | None, cp_api_url: str, hmac_secret: str
) -> ServiceOut:
    if not re.fullmatch(SLUG_PATTERN, slug):
        raise ValueError("slug invalid")
    _require_https(cp_api_url)
    ciphertext = encrypt_secret(hmac_secret)
    try:
        with connection() as conn:
            sid = services_repo.insert_service(conn, slug, name, operator, cp_api_url, ciphertext)
            row = services_repo.get_by_id(conn, sid)
    except psycopg.errors.UniqueViolation as exc:
        raise ServiceExistsError(slug) from exc
    return _to_out(row)


def get_active_service(slug: str) -> ServiceRuntime | None:
    with connection() as conn:
        row = services_repo.get_by_slug(conn, slug)
    if not row or row["status"] != "active":
        return None
    return ServiceRuntime(
        id=str(row["id"]), slug=row["slug"], cp_api_url=row["cp_api_url"], status=row["status"]
    )


def get_service_secret(slug: str) -> str:
    """Dekripsi hmac_secret untuk klien CP (server-side only)."""
    with connection() as conn:
        row = services_repo.get_by_slug(conn, slug)
    if not row:
        raise ServiceNotFoundError(slug)
    return decrypt_secret(bytes(row["hmac_secret"]))


def list_services() -> list[ServiceOut]:
    with connection() as conn:
        rows = services_repo.list_all(conn)
    return [_to_out(r) for r in rows]


def update_service(
    service_id: str,
    *,
    name: str | None = None,
    operator: str | None = None,
    cp_api_url: str | None = None,
    hmac_secret: str | None = None,
    status: str | None = None,
) -> ServiceOut:
    if cp_api_url is not None:
        _require_https(cp_api_url)
    ciphertext = encrypt_secret(hmac_secret) if hmac_secret is not None else None
    with connection() as conn:
        row = services_repo.update_service(
            conn,
            service_id,
            name=name,
            operator=operator,
            cp_api_url=cp_api_url,
            hmac_secret=ciphertext,
            status=status,
        )
    if not row:
        raise ServiceNotFoundError(service_id)
    return _to_out(row)
