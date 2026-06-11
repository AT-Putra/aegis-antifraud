"""Kontrak Scoring (`03 §3`): session/init, score, signals."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from aegis.schemas.common import ATTR_PATTERN, SLUG_PATTERN, TRX_ID_PATTERN


# --- session/init ---
class SessionInitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trx_id: str = Field(pattern=TRX_ID_PATTERN)
    service: str = Field(pattern=SLUG_PATTERN)
    campaign: str = Field(pattern=SLUG_PATTERN)
    source: str | None = Field(default=None, pattern=ATTR_PATTERN)
    pub_id: str | None = Field(default=None, pattern=ATTR_PATTERN)
    source_params: dict[str, str] | None = None


class SessionInitResponse(BaseModel):
    session_token: str
    expires_at: datetime


# --- signals (client mengirim; IP intel & device-info diturunkan server) ---
class Screen(BaseModel):
    model_config = ConfigDict(extra="ignore")
    width: int | None = None
    height: int | None = None
    availWidth: int | None = None
    availHeight: int | None = None
    colorDepth: int | None = None
    devicePixelRatio: float | None = None


class WebGL(BaseModel):
    model_config = ConfigDict(extra="ignore")
    vendor: str | None = None
    renderer: str | None = None
    params_hash: str | None = None


class BrowserEnvironment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    is_webview: bool | None = None
    webview_type: Literal["android_wv", "wkwebview"] | None = None
    inapp_browser: Literal["facebook", "instagram", "tiktok", "line", "unknown"] | None = None
    is_standalone: bool | None = None


class Fingerprint(BaseModel):
    model_config = ConfigDict(extra="ignore")
    screen: Screen | None = None
    webgl: WebGL | None = None
    canvas_hash: str | None = None
    audio_hash: str | None = None
    fonts: list[str] | None = None
    timezone: str | None = None
    languages: list[str] | None = None
    hardwareConcurrency: int | None = None
    deviceMemory: float | None = None
    platform: str | None = None
    maxTouchPoints: int | None = None
    storage_caps: dict[str, bool] | None = None
    ua_data: dict | None = None
    browser_environment: BrowserEnvironment | None = None


class Behavior(BaseModel):
    model_config = ConfigDict(extra="ignore")
    timing: dict | None = None
    mouse: dict | None = None
    scroll: dict | None = None
    touch: dict | None = None
    sensor: dict | None = None


class AutomationHints(BaseModel):
    model_config = ConfigDict(extra="ignore")
    webdriver: bool | None = None
    headless_hints: bool | None = None
    isTrusted_cta: bool | None = None
    webgl_software_render: bool | None = None
    automation_globals: list[str] | None = None
    viewport_anomaly: bool | None = None


class Integrity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    ever_visible: bool | None = None
    visibility_state: str | None = None
    iframe_embedded: bool | None = None
    time_skew_ms: int | None = None
    touch_device_consistent: bool | None = None


class Attribution(BaseModel):
    model_config = ConfigDict(extra="ignore")
    referrer: str | None = None
    locale_consistent: bool | None = None


class Signals(BaseModel):
    model_config = ConfigDict(extra="ignore")
    fingerprint: Fingerprint
    behavior: Behavior
    automation_hints: AutomationHints | None = None
    integrity: Integrity | None = None
    attribution: Attribution | None = None


# --- score ---
class ScoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trx_id: str = Field(pattern=TRX_ID_PATTERN)
    service: str = Field(pattern=SLUG_PATTERN)
    campaign: str = Field(pattern=SLUG_PATTERN)
    source: str | None = Field(default=None, pattern=ATTR_PATTERN)
    pub_id: str | None = Field(default=None, pattern=ATTR_PATTERN)
    source_params: dict[str, str] | None = None  # D2: dikirim ulang agar tersimpan ke OLAP
    session_token: str
    schema_version: str
    client_ts: datetime | None = None
    signals: Signals


class AllowResponse(BaseModel):
    decision: Literal["allow"] = "allow"
    redirect_url: str


class BlockResponse(BaseModel):
    decision: Literal["block"] = "block"
    notice: str = "Permintaan tidak dapat diproses."
