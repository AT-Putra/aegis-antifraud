"""JWT untuk dashboard (`03 §2.1/§6`). HS256, login sederhana (tanpa refresh rilis-1)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from aegis.config import get_settings

JWT_TTL_SECONDS = 8 * 3600
_ALGO = "HS256"
_bearer = HTTPBearer(auto_error=True)


def create_token(sub: str, role: str) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=JWT_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(claims, get_settings().jwt_secret, algorithm=_ALGO)


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=[_ALGO])


def require_role(*roles: str) -> Callable[..., dict]:
    """Dependency FastAPI: validasi JWT + (opsional) batasi role. Dipakai router T-12/T-15."""

    def dependency(cred: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
        try:
            claims = decode_token(cred.credentials)
        except jwt.PyJWTError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from exc
        if roles and claims.get("role") not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "forbidden")
        return claims

    return dependency
