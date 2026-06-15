"""Router Admin (`03 §6`): config versioned, settings, feedback, model, users, services.

Semua `/v1/admin/*` butuh role admin (AC-ADMIN-03 → 403). `/v1/feedback` (submit) =
user/admin. Service secret write-only (tak pernah dikembalikan). Aktivasi model = approval.
"""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from aegis.api.deps import current_admin, current_user, err
from aegis.core.logging import audit
from aegis.db.oltp import (
    model_versions_repo,
    retrain_jobs_repo,
    rule_configs_repo,
    settings_repo,
    users_repo,
)
from aegis.db.postgres import connection
from aegis.registry import campaign as campaign_registry
from aegis.registry import service as registry
from aegis.registry.errors import (
    CampaignExistsError,
    CampaignNotFoundError,
    ServiceExistsError,
    ServiceNotFoundError,
)
from aegis.schemas.admin import (
    CampaignCreate,
    CampaignOut,
    CampaignUpdate,
    ConfigOut,
    ConfigUpdate,
    ConfigVersionItem,
    FeedbackCreate,
    FeedbackReview,
    ModelOut,
    RetrainJob,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
    SettingItem,
    SettingUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)
from aegis.security import origins
from aegis.security.jwt_auth import verify_csrf
from aegis.security.passwords import hash_password
from aegis.services import feedback as feedback_svc

# CSRF double-submit (ADR-015) berlaku ke semua mutasi cookie-auth router ini; GET dilewati.
router = APIRouter(prefix="/v1", dependencies=[Depends(verify_csrf)])


# --- Config (versioned) ---
@router.get("/admin/config", response_model=ConfigOut)
def get_config(_admin: dict = Depends(current_admin)):
    with connection() as conn:
        row = rule_configs_repo.get_active(conn)
    if row is None:
        return err(404, "no_active_config", "tidak ada konfigurasi aktif")
    return ConfigOut(
        version=row["version"],
        params=row["params"] or {},
        threshold=float(row["threshold"]),
        blend_weights=row["blend_weights"] or {},
        guidelines=row.get("defaults_range_meta") or {},
    )


@router.put("/admin/config")
def put_config(req: ConfigUpdate, admin: dict = Depends(current_admin)) -> dict:
    with connection() as conn:
        version = rule_configs_repo.insert_version(
            conn,
            params=req.params,
            threshold=req.threshold,
            blend_weights=req.blend_weights,
            created_by=str(admin["id"]),
        )
    audit("config_update", actor=admin["username"], version=version)
    return {"version": version}


@router.get("/admin/config/versions", response_model=list[ConfigVersionItem])
def list_config_versions(_admin: dict = Depends(current_admin)) -> list[ConfigVersionItem]:
    with connection() as conn:
        rows = rule_configs_repo.list_versions(conn)
    return [ConfigVersionItem(**r) for r in rows]


@router.get("/admin/config/{version}")
def get_config_version(version: int, _admin: dict = Depends(current_admin)):
    """Ambil params versi tertentu (rollback satu-klik dashboard, 03 §6 / 2026-06-12)."""
    with connection() as conn:
        row = rule_configs_repo.get_by_version(conn, version)
    if row is None:
        return err(404, "config_version_not_found", "versi config tidak ditemukan")
    return {
        "version": row["version"],
        "params": row["params"] or {},
        "threshold": float(row["threshold"]),
        "blend_weights": row["blend_weights"] or {},
        "guidelines": row.get("defaults_range_meta") or {},
        "active": row["active"],
    }


# --- Settings ---
@router.get("/admin/settings", response_model=list[SettingItem])
def get_settings_list(_admin: dict = Depends(current_admin)) -> list[SettingItem]:
    with connection() as conn:
        rows = settings_repo.list_all(conn)
    return [SettingItem(**r) for r in rows]


@router.put("/admin/settings", response_model=SettingItem)
def put_setting(req: SettingUpdate, admin: dict = Depends(current_admin)) -> SettingItem:
    with connection() as conn:
        settings_repo.upsert(conn, req.key, req.value, updated_by=str(admin["id"]))
    return SettingItem(key=req.key, value=req.value)


# --- Feedback ---
@router.post("/feedback")
def submit_feedback(req: FeedbackCreate, user: dict = Depends(current_user)) -> dict:
    fid = feedback_svc.submit_feedback(
        flagged_label=req.flagged_label,
        trx_id=req.trx_id,
        decision_id=str(req.decision_id) if req.decision_id else None,
        user_id=str(user["id"]),
        note=req.note,
    )
    return {"id": fid}


@router.get("/admin/feedback")
def list_feedback(status: str = "pending", _admin: dict = Depends(current_admin)) -> list[dict]:
    if status == "pending":
        return feedback_svc.list_pending()
    with connection() as conn:
        from aegis.db.oltp import feedback_repo

        return feedback_repo.list_by_status(conn, status)


@router.put("/admin/feedback/{feedback_id}/review")
def review_feedback(feedback_id: str, req: FeedbackReview, admin: dict = Depends(current_admin)):
    row = feedback_svc.review_feedback(feedback_id, req.review_status, str(admin["id"]))
    if row is None:
        return err(404, "feedback_not_found", "feedback tidak ditemukan")
    return row


# --- Model & retraining ---
@router.get("/admin/models", response_model=list[ModelOut])
def list_models(_admin: dict = Depends(current_admin)) -> list[ModelOut]:
    with connection() as conn:
        rows = model_versions_repo.list_all(conn)
    return [ModelOut(**r) for r in rows]


@router.post("/admin/models/{model_id}/activate", response_model=ModelOut)
def activate_model(model_id: str, _admin: dict = Depends(current_admin)):
    with connection() as conn:
        row = model_versions_repo.activate(conn, model_id)
    if row is None:
        return err(404, "model_not_found", "versi model tidak ditemukan")
    audit("model_activate", actor=_admin["username"], model_id=model_id, version=row["version"])
    # Catatan: model runtime dimuat di lifespan → efektif setelah restart (hot-reload = future).
    return ModelOut(**row)


@router.post("/admin/retrain", response_model=RetrainJob)
def trigger_retrain(admin: dict = Depends(current_admin)) -> RetrainJob:
    with connection() as conn:
        job_id = retrain_jobs_repo.create_job(conn, requested_by=str(admin["id"]))
    # Eksekusi training nyata = T-17 (worker). Di sini hanya catat job (status queued).
    return RetrainJob(job_id=job_id, status="queued")


@router.get("/admin/retrain/{job_id}", response_model=RetrainJob)
def get_retrain(job_id: str, _admin: dict = Depends(current_admin)):
    with connection() as conn:
        row = retrain_jobs_repo.get_job(conn, job_id)
    if row is None:
        return err(404, "job_not_found", "job retrain tidak ditemukan")
    return RetrainJob(job_id=row["id"], status=row["status"], metrics=row["metrics"])


# --- User management ---
@router.get("/admin/users", response_model=list[UserOut])
def list_users(_admin: dict = Depends(current_admin)) -> list[UserOut]:
    with connection() as conn:
        rows = users_repo.list_all(conn)
    return [UserOut(**r) for r in rows]


@router.post("/admin/users")
def create_user(req: UserCreate, _admin: dict = Depends(current_admin)):
    try:
        with connection() as conn:
            uid = users_repo.insert_user(
                conn, username=req.username, password_hash=hash_password(req.password),
                role=req.role,
            )
    except psycopg.errors.UniqueViolation:
        return err(409, "username_exists", "username sudah dipakai")
    audit("user_create", actor=_admin["username"], username=req.username, role=req.role)
    return {"id": uid}


@router.put("/admin/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, req: UserUpdate, _admin: dict = Depends(current_admin)):
    pw_hash = hash_password(req.password) if req.password else None
    with connection() as conn:
        row = users_repo.update_user(
            conn, user_id, role=req.role, active=req.active, password_hash=pw_hash
        )
    if row is None:
        return err(404, "user_not_found", "user tidak ditemukan")
    return UserOut(**row)


# --- Service registry (secret write-only) ---
@router.get("/admin/services", response_model=list[ServiceOut])
def list_services(_admin: dict = Depends(current_admin)) -> list[ServiceOut]:
    return registry.list_services()


@router.post("/admin/services")
def create_service(req: ServiceCreate, _admin: dict = Depends(current_admin)):
    try:
        out = registry.register_service(
            req.slug, req.name, req.operator, req.cp_api_url, req.hmac_secret
        )
    except ServiceExistsError:
        return err(409, "service_exists", "slug sudah dipakai")
    except ValueError as exc:
        return err(400, "invalid_service", str(exc))
    return {"id": str(out.id)}


@router.put("/admin/services/{service_id}", response_model=ServiceOut)
def update_service(service_id: str, req: ServiceUpdate, _admin: dict = Depends(current_admin)):
    try:
        return registry.update_service(
            service_id, name=req.name, operator=req.operator, cp_api_url=req.cp_api_url,
            hmac_secret=req.hmac_secret, status=req.status,
        )
    except ServiceNotFoundError:
        return err(404, "service_not_found", "service tidak ditemukan")
    except ValueError as exc:
        return err(400, "invalid_service", str(exc))


# --- Campaign registry (pre-landing portabel; F-16) ---
@router.get("/admin/campaigns", response_model=list[CampaignOut])
def list_campaigns(
    service: str | None = None, _admin: dict = Depends(current_admin)
) -> list[CampaignOut]:
    return campaign_registry.list_campaigns(service)


@router.post("/admin/campaigns")
def create_campaign(req: CampaignCreate, _admin: dict = Depends(current_admin)):
    try:
        out = campaign_registry.register_campaign(
            req.slug, req.name, req.service, req.allowed_origins
        )
    except CampaignExistsError:
        return err(409, "campaign_exists", "slug campaign sudah dipakai")
    except ServiceNotFoundError:
        return err(404, "service_not_found", "service tidak ditemukan")
    except ValueError as exc:
        return err(400, "invalid_campaign", str(exc))
    origins.invalidate_cache()  # CORS dinamis (D1) lihat origin campaign baru
    return {"id": str(out.id)}


@router.put("/admin/campaigns/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: str, req: CampaignUpdate, _admin: dict = Depends(current_admin)):
    try:
        out = campaign_registry.update_campaign(
            campaign_id, name=req.name, allowed_origins=req.allowed_origins, status=req.status,
        )
    except CampaignNotFoundError:
        return err(404, "campaign_not_found", "campaign tidak ditemukan")
    except ValueError as exc:
        return err(400, "invalid_campaign", str(exc))
    origins.invalidate_cache()
    return out
