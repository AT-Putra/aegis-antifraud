"""Router scoring: session/init + score (`03 §3`, TRD §5 Alur 1+1b)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from aegis.api.deps import client_ip, err
from aegis.cp.client import mint_weboptin_url
from aegis.db.olap import traffic_repo
from aegis.db.oltp import decisions_repo
from aegis.db.postgres import connection
from aegis.features.device_info import parse_device_info
from aegis.features.extract import extract_features
from aegis.features.ip_intel import enrich_ip
from aegis.features.schema import FeatureInput
from aegis.fingerprint.service import lookup_or_register
from aegis.registry.service import get_active_service, get_service_secret
from aegis.schemas.scoring import ScoreRequest, SessionInitRequest
from aegis.scoring.engine import score
from aegis.security import origins, ratelimit
from aegis.security.tokens import SessionTokenError, issue, verify_and_consume

router = APIRouter(prefix="/v1")

_RL_LIMIT = 120
_RL_WINDOW = 60


def _check_origin(request: Request) -> JSONResponse | None:
    origin = request.headers.get("origin")
    if origin and not origins.is_allowed_origin(origin):
        return err(403, "forbidden_origin", "origin tidak diizinkan")
    return None


@router.post("/session/init")
def session_init(req: SessionInitRequest, request: Request):
    if (resp := _check_origin(request)) is not None:
        return resp
    ip = client_ip(request) or "unknown"
    if not ratelimit.allow(f"init:{ip}", _RL_LIMIT, _RL_WINDOW):
        return err(429, "rate_limited", "terlalu banyak permintaan")
    if get_active_service(req.service) is None:
        return err(404, "service_not_found", "layanan tidak ditemukan / nonaktif")
    token, expires_at = issue(req.trx_id)
    return {"session_token": token, "expires_at": expires_at.isoformat()}


def _finalize_allow(svc, req: ScoreRequest):
    """Mint URL web-opt-in via CP; update weboptin_status; balas allow / 502."""
    secret = get_service_secret(svc.slug)
    res = mint_weboptin_url(
        svc.cp_api_url, secret,
        trx_id=req.trx_id, service=req.service, source=req.source, pub_id=req.pub_id,
    )
    with connection() as conn:
        decisions_repo.update_weboptin(conn, req.trx_id, res.weboptin_status, res.host)
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
        verify_and_consume(req.session_token, req.trx_id)
    except SessionTokenError:
        return err(401, "invalid_session", "session token tidak valid")

    svc = get_active_service(req.service)
    if svc is None:
        return err(404, "service_not_found", "layanan tidak ditemukan / nonaktif")

    # Replay: kembalikan keputusan pertama (tidak scoring ulang) — TRD §6.
    with connection() as conn:
        existing = decisions_repo.get_by_trx(conn, req.trx_id)
    if existing:
        return _block() if existing["decision"] == "block" else _finalize_allow(svc, req)

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
    outcome = score(feature_input, config=cfg, models=request.app.state.models)

    with connection() as conn:
        decisions_repo.insert_decision(
            conn,
            trx_id=req.trx_id,
            device_id=device.device_id,
            service_id=svc.id,
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
    try:
        traffic_repo.write_event(
            trx_id=req.trx_id, device_id=device.device_id, service=req.service,
            source=req.source, pub_id=req.pub_id,
            signals=req.signals.model_dump(), features=extract_features(feature_input),
            ip_intel=ip_intel, decision=outcome.decision, final_score=outcome.final_score,
            weboptin_status="na",  # status mint final di OLTP; OLAP snapshot awal
            rules_version=outcome.rules_version, model_version=outcome.model_version,
        )
    except Exception:
        pass  # OLAP loss-tolerant (K4)

    if outcome.decision == "block":
        return _block()
    return _finalize_allow(svc, req)
