"""Enkripsi secret at-rest dengan AES-256-GCM (authenticated). TQ-08.

Dipakai untuk `services.hmac_secret` (ciphertext BYTEA). Master key diturunkan
dari `SECRET_ENC_KEY` (.env) via SHA-256 → selalu 32 byte. Produksi: pakai key acak kuat.
"""

from __future__ import annotations

import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from aegis.config import get_settings

_NONCE_BYTES = 12


def _key() -> bytes:
    return hashlib.sha256(get_settings().secret_enc_key.encode()).digest()


def encrypt_secret(plaintext: str) -> bytes:
    """Kembalikan nonce(12) + ciphertext+tag. Tamper terdeteksi saat decrypt (GCM)."""
    nonce = os.urandom(_NONCE_BYTES)
    ct = AESGCM(_key()).encrypt(nonce, plaintext.encode(), None)
    return nonce + ct


def decrypt_secret(blob: bytes) -> str:
    nonce, ct = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
    return AESGCM(_key()).decrypt(nonce, ct, None).decode()
