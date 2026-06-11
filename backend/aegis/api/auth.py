"""Router Auth & profil (`03 §6`): login (JWT), logout, /users/me. JWT sub = username."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from aegis.api.deps import client_ip, current_user, err
from aegis.db.oltp import users_repo
from aegis.db.postgres import connection
from aegis.schemas.admin import LoginRequest, UserMe, UserMeUpdate
from aegis.security import ratelimit
from aegis.security.jwt_auth import create_token
from aegis.security.passwords import verify_password

router = APIRouter(prefix="/v1")

_RL_LIMIT = 10
_RL_WINDOW = 60


@router.post("/auth/login")
def login(req: LoginRequest, request: Request):
    ip = client_ip(request) or "unknown"
    if not ratelimit.allow(f"login:{ip}", _RL_LIMIT, _RL_WINDOW):
        return err(429, "rate_limited", "terlalu banyak percobaan login")
    with connection() as conn:
        user = users_repo.get_by_username(conn, req.username)
    if user is None or not user["active"] or not verify_password(
        req.password, user["password_hash"]
    ):
        return err(401, "invalid_credentials", "username atau password salah")
    return {"jwt": create_token(user["username"], user["role"]), "role": user["role"]}


@router.post("/auth/logout")
def logout(_user: dict = Depends(current_user)) -> dict:
    # JWT stateless (tanpa server-side session di rilis-1) → klien buang token.
    return {"status": "ok"}


@router.get("/users/me", response_model=UserMe)
def get_me(user: dict = Depends(current_user)) -> UserMe:
    return UserMe(**user)


@router.put("/users/me", response_model=UserMe)
def update_me(req: UserMeUpdate, user: dict = Depends(current_user)) -> UserMe:
    with connection() as conn:
        updated = users_repo.update_timezone(conn, str(user["id"]), req.timezone)
    return UserMe(**updated)
