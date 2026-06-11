"""Error domain registry."""

from __future__ import annotations


class ServiceExistsError(Exception):
    """Slug sudah terdaftar."""


class ServiceNotFoundError(Exception):
    """Service tidak ditemukan."""


class CampaignExistsError(Exception):
    """Slug campaign sudah terdaftar."""


class CampaignNotFoundError(Exception):
    """Campaign tidak ditemukan / bukan milik service."""
