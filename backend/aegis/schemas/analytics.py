"""Kontrak Analytics / SSE / Search (`03 §7`). Atribusi berjenjang service→source→pub_id."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SummaryOut(BaseModel):
    total: int
    allow: int
    block: int
    weboptin_failed: int
    fraud_est: int
    complaints: int
    charging_fail_breakdown: dict[str, int]


class TimeseriesPoint(BaseModel):
    bucket_ts: datetime
    value: float


class BreakdownItem(BaseModel):
    key: str
    count: int


class SearchResultItem(BaseModel):
    trx_id: str
    device_id: str | None = None
    service: str | None = None
    campaign: str | None = None
    source: str | None = None
    pub_id: str | None = None
    decision: str
    weboptin_status: str | None = None
    final_score: float | None = None
    ts: datetime


class DecisionDetail(BaseModel):
    trx_id: str
    device_id: str | None = None
    service: str | None = None
    campaign: str | None = None
    source: str | None = None
    pub_id: str | None = None
    decision: str
    weboptin_status: str | None = None
    weboptin_host: str | None = None
    final_score: float | None = None
    score_breakdown: dict
    signals: dict
    ip_intelligence: dict
    device_info: dict
    rules_version: int | None = None
    model_version: int | None = None
    outcome: dict | None = None
