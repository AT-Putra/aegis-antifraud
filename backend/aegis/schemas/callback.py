"""Kontrak Callback Billing dua fase (`03 §4`)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aegis.schemas.common import TRX_ID_PATTERN


class SubscriptionCallback(BaseModel):
    """Hanya untuk langganan SUKSES (gagal langganan TIDAK di-callback)."""

    model_config = ConfigDict(extra="forbid")

    event: Literal["subscription"]
    trx_id: str = Field(pattern=TRX_ID_PATTERN)
    charging_status: Literal["success", "failed"]
    charging_fail_reason: Literal["insufficient_balance", "daily_limit_reached"] | None = None
    service_id: str
    msisdn_hash: str  # sudah di-hash oleh telco (CP tak pegang plaintext)
    event_time: datetime


class ComplaintCallback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: Literal["complaint"]
    trx_id: str = Field(pattern=TRX_ID_PATTERN)
    event_time: datetime
