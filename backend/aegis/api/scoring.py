"""Router scoring: session/init + score (`03 §3`, TRD §5 Alur 1+1b)."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from aegis.api.deps import client_ip, err
from aegis.core import metrics
from aegis.cp.client import mint_weboptin_url
from aegis.db.olap import traffic_repo
from aegis.db.oltp import decisions_repo
from aegis.db.postgres import connection
from aegis.features.device_info import parse_device_info
from aegis.features.extract import extract_features
from aegis.features.ip_intel import enrich_ip
from aegis.features.schema import FeatureInput
from aegis.fingerprint.service import lookup_or_register
from aegis.registry.campaign import get_active_campaign
from aegis.registry.service import get_active_service, get_service_secret
from aegis.schemas.scoring import ScoreRequest, SessionInitRequest
from aegis.scoring.engine import score
from aegis.security import ratelimit
from aegis.security.tokens import SessionTokenError, issue, verify_and_consume

router = APIRouter(prefix="/v1")

_RL_LIMIT = 120
_RL_WINDOW = 60


def _resolve_campaign(req, request: Request):
    """Validasi service+campaign (milik service) + CORS per-campaign. -> (camp, err|None)."""
    if get_active_service(req.service) is None:
        return None, err(404, "service_not_found", "layanan tidak ditemukan / nonaktif")
    camp = get_active_campaign(req.campaign)
    if camp is None or camp.service != req.service:
        return None, err(404, "campaign_not_found", "campaign tidak ditemukan / nonaktif")
    origin = request.headers.get("origin")
    if not origin or origin not in camp.allowed_origins:
        return None, err(403, "forbidden_origin", "origin tidak diizinkan untuk campaign ini")
    return camp, None


@router.post("/session/init")
def session_init(req: SessionInitRequest, request: Request):
    ip = client_ip(request) or "unknown"
    if not ratelimit.allow(f"init:{ip}", _RL_LIMIT, _RL_WINDOW):
        return err(429, "rate_limited", "terlalu banyak permintaan")
    _camp, error = _resolve_campaign(req, request)
    if error is not None:
        return error
    token, expires_at = issue(req.trx_id, req.service, req.campaign)
    return {"session_token": token, "expires_at": expires_at.isoformat()}


def _finalize_allow(svc, req: ScoreRequest):
    """Mint URL web-opt-in via CP; update weboptin_status OLTP; balikkan MintResult."""
    secret = get_service_secret(svc.slug)
    _t = time.perf_counter()
    res = mint_weboptin_url(
        svc.cp_api_url, secret,
        trx_id=req.trx_id, service=req.service, source=req.source, pub_id=req.pub_id,
    )
    metrics.mint_latency.observe(time.perf_counter() - _t)
    if res.weboptin_status == "failed":
        metrics.mint_failures.labels(res.reason or "unknown").inc()
    with connection() as conn:
        decisions_repo.update_weboptin(conn, req.trx_id, res.weboptin_status, res.host)
    return res


def _allow_response(res):
    if res.weboptin_status == "minted":
        return {"decision": "allow", "redirect_url": res.redirect_url}
    return err(502, "weboptin_unavailable", "tidak dapat mengambil URL web-opt-in")


def _block():
    return {"decision": "block", "notice": "Permintaan tidak dapat diproses."}


@router.post("/score")
def score_endpoint(req: ScoreRequest, request: Request):
    ip = client_ip(request) or "unknown"
    if not ratelimit.allow(f"score:{ip}", _RL_LIMIT, _RL_WINDOW):
        return err(429, "rate_limited", "terlalu banyak permintaan")
    try:
        verify_and_consume(req.session_token, req.trx_id, req.service, req.campaign)
    except SessionTokenError:
        return err(401, "invalid_session", "session token tidak valid")

    camp, error = _resolve_campaign(req, request)
    if error is not None:
        return error
    svc = get_active_service(req.service)

    # Replay: kembalikan keputusan pertama (tidak scoring ulang) — TRD §6.
    with connection() as conn:
        existing = decisions_repo.get_by_trx(conn, req.trx_id)
    if existing:
        if existing["decision"] == "block":
            return _block()
        return _allow_response(_finalize_allow(svc, req))

    device = lookup_or_register(req.signals.fingerprint)
    ip_intel = enrich_ip(ip)
    device_info = parse_device_info(
        request.headers.get("user-agent"), req.signals.fingerprint.ua_data
    )
    feature_input = FeatureInput(
        signals=req.signals,
        ip_intel=ip_intel,
        device_info=device_info,
        device_history={"event_count": device.event_count, "is_new": device.is_new},
    )
    cfg = request.app.state.config
    if cfg is None:
        return err(503, "not_ready", "konfigurasi scoring belum siap")
    _t = time.perf_counter()
    outcome = score(feature_input, config=cfg, models=request.app.state.models)
    metrics.score_latency.observe(time.perf_counter() - _t)
    metrics.decisions.labels(outcome.decision).inc()
    metrics.final_score.observe(outcome.final_score)

    with connection() as conn:
        decisions_repo.insert_decision(
            conn,
            trx_id=req.trx_id,
            device_id=device.device_id,
            service_id=svc.id,
            campaign_id=camp.id,
            source=req.source,
            pub_id=req.pub_id,
            final_score=outcome.final_score,
            decision=outcome.decision,
            threshold_used=outcome.threshold_used,
            rules_version=outcome.rules_version,
            model_version=outcome.model_version,
            reason=outcome.reason,
            weboptin_status="na",
        )
    # Selesaikan keputusan dulu agar weboptin_status final (minted/failed/na) ikut ke OLAP.
    if outcome.decision == "block":
        weboptin_status, response = "na", _block()
    else:
        res = _finalize_allow(svc, req)
        weboptin_status, response = res.weboptin_status, _allow_response(res)

    is_webview = None
    if req.signals.fingerprint.browser_environment is not None:
        is_webview = req.signals.fingerprint.browser_environment.is_webview
    try:
        traffic_repo.write_event(
            trx_id=req.trx_id, device_id=device.device_id, service=req.service,
            campaign=req.campaign, source=req.source, pub_id=req.pub_id,
            signals=req.signals.model_dump(), features=extract_features(feature_input),
            ip_intel=ip_intel, decision=outcome.decision, final_score=outcome.final_score,
            weboptin_status=weboptin_status,
            rules_version=outcome.rules_version, model_version=outcome.model_version,
            reason=outcome.reason,
            device_info=device_info, is_webview=is_webview,
            score_breakdown=outcome.score_breakdown, source_params=req.source_params,
        )
    except Exception:
        pass  # OLAP loss-tolerant (K4)

    return response
