"""Router callback billing dua fase (`03 §4`, HMAC inbound)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request

from aegis.api.deps import err
from aegis.config import get_settings
from aegis.schemas.callback import ComplaintCallback, SubscriptionCallback
from aegis.security.hmac_auth import verify_inbound
from aegis.services import labeling

router = APIRouter(prefix="/v1")


@router.post("/callback/billing")
async def callback_billing(request: Request):
    raw = await request.body()
    ts = request.headers.get("x-aegis-timestamp", "")
    sig = request.headers.get("x-aegis-signature", "")
    secret = get_settings().billing_hmac_secret
    if not verify_inbound(secret, ts, raw.decode("utf-8"), sig):
        return err(401, "invalid_signature", "signature / timestamp tidak valid")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return err(422, "bad_payload", "body bukan JSON valid")

    event = data.get("event")
    if event == "subscription":
        labeling.record_subscription(SubscriptionCallback.model_validate(data))
    elif event == "complaint":
        labeling.record_complaint(ComplaintCallback.model_validate(data))
    else:
        return err(422, "bad_event", "event tidak dikenal")
    return {"status": "ok"}
