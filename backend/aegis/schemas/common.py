"""Pola & tipe bersama lintas-kontrak (`03 §2`)."""

from __future__ import annotations

# Pola identitas (allowlist anti-injeksi; parameterized query tetap wajib di DB)
TRX_ID_PATTERN = r"^[A-Za-z0-9._:-]{1,128}$"
SLUG_PATTERN = r"^[a-z0-9-]{1,64}$"
ATTR_PATTERN = r"^[A-Za-z0-9._:-]{1,64}$"  # source / pub_id (nullable)
