"""AC-SEC-04 (sebagian): JWT roundtrip + role; token invalid ditolak."""

import jwt
import pytest

from aegis.security.jwt_auth import create_token, decode_token
from aegis.security.origins import is_allowed_origin


def test_jwt_roundtrip_role() -> None:
    token = create_token("user-1", "admin")
    claims = decode_token(token)
    assert claims["sub"] == "user-1"
    assert claims["role"] == "admin"


def test_jwt_invalid_token_rejected() -> None:
    with pytest.raises(jwt.PyJWTError):
        decode_token("not.a.jwt")


def test_origin_whitelist() -> None:
    # .env dev: ALLOWED_ORIGINS=http://localhost
    assert is_allowed_origin("http://localhost") is True
    assert is_allowed_origin("http://evil.example") is False
    assert is_allowed_origin(None) is False
