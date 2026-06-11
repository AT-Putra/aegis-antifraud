"""AC-SEC-05: enkripsi secret AES-256-GCM + hashing password argon2."""

import pytest
from cryptography.exceptions import InvalidTag

from aegis.security.crypto import decrypt_secret, encrypt_secret
from aegis.security.passwords import hash_password, verify_password


def test_encrypt_decrypt_roundtrip() -> None:
    blob = encrypt_secret("super-secret-hmac-key")
    assert decrypt_secret(blob) == "super-secret-hmac-key"


def test_ciphertext_differs_from_plaintext_and_nondeterministic() -> None:
    a = encrypt_secret("same")
    b = encrypt_secret("same")
    assert b"same" not in a
    assert a != b  # nonce acak → ciphertext berbeda


def test_tamper_detected() -> None:
    blob = bytearray(encrypt_secret("x"))
    blob[-1] ^= 0x01  # ubah 1 byte tag/ciphertext
    with pytest.raises(InvalidTag):
        decrypt_secret(bytes(blob))


def test_password_hash_verify() -> None:
    h = hash_password("hunter2")
    assert h != "hunter2"
    assert verify_password("hunter2", h) is True
    assert verify_password("wrong", h) is False
