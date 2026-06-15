"""Kontrak Auth / Users / Config / Feedback / Model / Service (`03 §6`)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from aegis.schemas.common import SLUG_PATTERN, TRX_ID_PATTERN

Role = Literal["admin", "user"]


# --- Auth & profil ---
class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    password: str


class LoginResponse(BaseModel):
    # ADR-015: JWT dikirim via cookie httpOnly `aegis_jwt`, BUKAN di body. Body hanya role.
    role: Role


class UserMe(BaseModel):
    id: UUID
    username: str
    role: Role
    timezone: str


class UserMeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    timezone: str


# --- User management ---
class UserOut(BaseModel):
    id: UUID
    username: str
    role: Role
    active: bool


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    password: str
    role: Role


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Role | None = None
    active: bool | None = None
    password: str | None = None


# --- Config (versioned) ---
class ConfigOut(BaseModel):
    version: int
    params: dict
    threshold: float
    blend_weights: dict
    guidelines: dict | None = None


class ConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    params: dict
    threshold: float
    blend_weights: dict


class ConfigVersionItem(BaseModel):
    version: int
    created_by: UUID | None = None
    created_at: datetime
    active: bool


# --- Settings ---
class SettingItem(BaseModel):
    key: str
    value: str


class SettingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    value: str


# --- Retrain ---
class RetrainJob(BaseModel):
    job_id: UUID
    status: Literal["queued", "running", "done", "failed"]
    metrics: dict | None = None


# --- Feedback ---
class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trx_id: str | None = Field(default=None, pattern=TRX_ID_PATTERN)
    decision_id: UUID | None = None
    flagged_label: Literal["human", "robot"]
    note: str | None = None


class FeedbackReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    review_status: Literal["accepted", "rejected"]


# --- Model ---
class ModelOut(BaseModel):
    id: UUID
    version: int
    algorithm: str
    trained_at: datetime | None = None
    metrics: dict
    active: bool


# --- Service registry (hmac_secret write-only: tak pernah di response) ---
class ServiceOut(BaseModel):
    id: UUID
    slug: str
    name: str
    operator: str | None = None
    cp_api_url: str
    status: Literal["active", "inactive"]
    created_at: datetime
    updated_at: datetime


class ServiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=SLUG_PATTERN)
    name: str
    operator: str | None = None
    cp_api_url: str = Field(pattern=r"^https://.+")
    hmac_secret: str  # write-only; disimpan terenkripsi (T-03/T-07)


class ServiceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    operator: str | None = None
    cp_api_url: str | None = Field(default=None, pattern=r"^https://.+")
    hmac_secret: str | None = None
    status: Literal["active", "inactive"] | None = None


# --- Campaign registry (pre-landing portabel; F-16) ---
class CampaignOut(BaseModel):
    id: UUID
    slug: str
    name: str
    service: str
    allowed_origins: list[str] = []
    status: Literal["active", "inactive"]
    created_at: datetime
    updated_at: datetime


class CampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=SLUG_PATTERN)
    name: str
    service: str = Field(pattern=SLUG_PATTERN)
    allowed_origins: list[str] = []


class CampaignUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    allowed_origins: list[str] | None = None
    status: Literal["active", "inactive"] | None = None
