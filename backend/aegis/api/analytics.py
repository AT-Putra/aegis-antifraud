"""Router Analytics / SSE / Search (`03 §7`). Read-only, di balik JWT (admin & user).

Atribusi berjenjang service→source→pub_id ditegakkan dengan meneruskan filter ke query
(AC-ANALYTICS-01). final_score & detail boleh tampil di sini (internal), tak pernah di
`/v1/score` publik (§3.2).
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from aegis.db.olap import analytics_repo
from aegis.schemas.analytics import (
    BreakdownItem,
    DecisionDetail,
    SearchResultItem,
    SummaryOut,
    TimeseriesPoint,
)
from aegis.security.jwt_auth import require_role

router = APIRouter(prefix="/v1", tags=["analytics"])
_guard = Depends(require_role("admin", "user"))

_From = Query(default=None, alias="from")
_To = Query(default=None, alias="to")


@router.get("/analytics/summary", response_model=SummaryOut)
def get_summary(
    from_: datetime | None = _From,
    to: datetime | None = _To,
    tz: str = "UTC",
    service: str | None = None,
    source: str | None = None,
    pub_id: str | None = None,
    _claims: dict = _guard,
) -> SummaryOut:
    data = analytics_repo.summary(
        from_, to, service=service, source=source, pub_id=pub_id
    )
    return SummaryOut(**data)


@router.get("/analytics/timeseries", response_model=list[TimeseriesPoint])
def get_timeseries(
    metric: str = "total",
    from_: datetime | None = _From,
    to: datetime | None = _To,
    granularity: str = "day",
    tz: str = "UTC",
    service: str | None = None,
    source: str | None = None,
    pub_id: str | None = None,
    _claims: dict = _guard,
) -> list[TimeseriesPoint]:
    try:
        rows = analytics_repo.timeseries(
            metric, from_, to, granularity=granularity, tz=tz,
            service=service, source=source, pub_id=pub_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return [TimeseriesPoint(**r) for r in rows]


@router.get("/analytics/breakdown", response_model=list[BreakdownItem])
def get_breakdown(
    dimension: str = "service",
    from_: datetime | None = _From,
    to: datetime | None = _To,
    tz: str = "UTC",
    service: str | None = None,
    source: str | None = None,
    _claims: dict = _guard,
) -> list[BreakdownItem]:
    try:
        rows = analytics_repo.breakdown(
            dimension, from_, to, tz=tz, service=service, source=source
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return [BreakdownItem(**r) for r in rows]


@router.get("/analytics/search", response_model=list[SearchResultItem])
def get_search(
    trx_id: str | None = None,
    device_id: str | None = None,
    decision: str | None = None,
    country: str | None = None,
    asn: int | None = None,
    service: str | None = None,
    source: str | None = None,
    pub_id: str | None = None,
    from_: datetime | None = _From,
    to: datetime | None = _To,
    webview: bool | None = None,
    browser: str | None = None,
    device_brand: str | None = None,
    device_model: str | None = None,
    os: str | None = None,
    charging_status: str | None = None,
    vpn: bool | None = None,
    weboptin_status: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _claims: dict = _guard,
) -> list[SearchResultItem]:
    rows = analytics_repo.search(
        trx_id=trx_id, device_id=device_id, decision=decision, country=country, asn=asn,
        service=service, source=source, pub_id=pub_id, from_ts=from_, to_ts=to,
        webview=webview, browser=browser, device_brand=device_brand,
        device_model=device_model, os=os, charging_status=charging_status, vpn=vpn,
        weboptin_status=weboptin_status, limit=limit, offset=offset,
    )
    return [SearchResultItem(**r) for r in rows]


@router.get("/analytics/decision/{trx_id}", response_model=DecisionDetail)
def get_decision_detail(trx_id: str, _claims: dict = _guard) -> DecisionDetail:
    data = analytics_repo.decision_detail(trx_id)
    if data is None:
        raise HTTPException(404, "decision_not_found")
    return DecisionDetail(**data)


def _sse(payload: dict, event: str) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, default=str)}\n\n"


@router.get("/stream")
def stream(
    tz: str = "UTC",
    service: str | None = None,
    source: str | None = None,
    pub_id: str | None = None,
    interval: float = Query(default=2.0, ge=0.5, le=30.0),
    limit: int | None = Query(default=None, ge=1),  # batas iterasi (uji); None = kontinu
    _claims: dict = _guard,
) -> StreamingResponse:
    """SSE: snapshot KPI bergulir + feed keputusan terbaru (K3, polling ~`interval` dtk)."""

    def gen() -> Iterator[str]:
        last_ts: datetime | None = None
        count = 0
        while True:
            try:
                kpi = analytics_repo.summary(
                    None, None, service=service, source=source, pub_id=pub_id
                )
                yield _sse(kpi, "kpi")
                recent = analytics_repo.recent_decisions(since=last_ts, limit=20)
                for row in reversed(recent):  # kronologis lama→baru
                    yield _sse(row, "decision")
                    last_ts = row["ts"]
            except Exception:  # OLAP loss-tolerant: stream tak boleh tumbang
                yield _sse({"error": "unavailable"}, "error")
            count += 1
            if limit is not None and count >= limit:
                return
            time.sleep(interval)

    return StreamingResponse(gen(), media_type="text/event-stream")
