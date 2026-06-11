"""Kontrak Aegis → Sistem CP (request URL web-opt-in) (`03 §5`)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from aegis.schemas.common import ATTR_PATTERN, SLUG_PATTERN, TRX_ID_PATTERN


class WebOptInRequest(BaseModel):
    """Body yang ditandatangani HMAC per-service & dikirim ke cp_api_url."""

    model_config = ConfigDict(extra="forbid")

    trx_id: str = Field(pattern=TRX_ID_PATTERN)
    service: str = Field(pattern=SLUG_PATTERN)
    source: str | None = Field(default=None, pattern=ATTR_PATTERN)
    pub_id: str | None = Field(default=None, pattern=ATTR_PATTERN)
    request_id: UUID
    requested_at: datetime


class WebOptInResponse(BaseModel):
    """Respons CP. `ok` → web_opt_in_url wajib; `error` → reason."""

    model_config = ConfigDict(extra="ignore")

    status: Literal["ok", "error"]
    web_opt_in_url: str | None = None
    reason: str | None = None
