"""Error domain registry."""

from __future__ import annotations


class ServiceExistsError(Exception):
    """Slug sudah terdaftar."""


class ServiceNotFoundError(Exception):
    """Service tidak ditemukan."""
