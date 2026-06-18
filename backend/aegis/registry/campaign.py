"""Logika campaign registry (T-21, F-16): pre-landing portabel + CORS per-campaign.

Campaign milik satu `service` (immutable). `allowed_origins` = whitelist CORS per-campaign
(origin pre-landing, bisa eksternal). Slug immutable; hapus = soft-delete (status).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import psycopg

from aegis.db.oltp import campaigns_repo, services_repo
from aegis.db.postgres import connection
from aegis.registry.countries import normalize_countries
from aegis.registry.errors import (
    CampaignExistsError,
    CampaignNotFoundError,
    ServiceNotFoundError,
)
from aegis.schemas.admin import CampaignOut
from aegis.schemas.common import SLUG_PATTERN


@dataclass
class CampaignRuntime:
    id: str
    slug: str
    service: str
    allowed_origins: list[str]
    allowed_countries: list[str]
    status: str


def _to_out(row: dict) -> CampaignOut:
    return CampaignOut(
        id=row["id"],
        slug=row["slug"],
        name=row["name"],
        service=row["service"],
        allowed_origins=list(row["allowed_origins"] or []),
        allowed_countries=list(row["allowed_countries"] or []),
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _validate_origins(origins: list[str]) -> None:
    for o in origins:
        if not (o.startswith("https://") or o.startswith("http://")):
            raise ValueError(f"origin tidak valid (harus http/https): {o}")


def register_campaign(
    slug: str, name: str, service: str,
    allowed_origins: list[str], allowed_countries: list[str] | None = None,
) -> CampaignOut:
    if not re.fullmatch(SLUG_PATTERN, slug):
        raise ValueError("slug invalid")
    _validate_origins(allowed_origins)
    countries = normalize_countries(allowed_countries or [])  # None/[] = ALL
    with connection() as conn:
        svc = services_repo.get_by_slug(conn, service)
        if svc is None:
            raise ServiceNotFoundError(service)
        try:
            cid = campaigns_repo.insert_campaign(
                conn, slug=slug, name=name, service_id=str(svc["id"]),
                allowed_origins=allowed_origins, allowed_countries=countries,
            )
        except psycopg.errors.UniqueViolation as exc:
            raise CampaignExistsError(slug) from exc
        row = campaigns_repo.get_by_id(conn, cid)
    return _to_out(row)


def get_active_campaign(slug: str) -> CampaignRuntime | None:
    with connection() as conn:
        row = campaigns_repo.get_by_slug(conn, slug)
    if not row or row["status"] != "active":
        return None
    return CampaignRuntime(
        id=str(row["id"]), slug=row["slug"], service=row["service"],
        allowed_origins=list(row["allowed_origins"] or []),
        allowed_countries=list(row["allowed_countries"] or []),
        status=row["status"],
    )


def list_campaigns(service: str | None = None) -> list[CampaignOut]:
    with connection() as conn:
        rows = campaigns_repo.list_all(conn, service)
    return [_to_out(r) for r in rows]


def update_campaign(
    campaign_id: str,
    *,
    name: str | None = None,
    allowed_origins: list[str] | None = None,
    allowed_countries: list[str] | None = None,
    status: str | None = None,
) -> CampaignOut:
    if allowed_origins is not None:
        _validate_origins(allowed_origins)
    if allowed_countries is not None:
        allowed_countries = normalize_countries(allowed_countries)  # [] = ALL
    with connection() as conn:
        row = campaigns_repo.update_campaign(
            conn, campaign_id, name=name, allowed_origins=allowed_origins,
            allowed_countries=allowed_countries, status=status,
        )
    if row is None:
        raise CampaignNotFoundError(campaign_id)
    return _to_out(row)
