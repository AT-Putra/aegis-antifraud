"""Ingest callback billing dua fase → outcomes (idempoten, orphan-aware). US-02, `03 §4`."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from aegis.db.olap import outcome_repo
from aegis.db.oltp import decisions_repo, outcomes_repo
from aegis.db.postgres import connection
from aegis.schemas.callback import ComplaintCallback, SubscriptionCallback

_log = logging.getLogger("aegis.labeling")


@dataclass
class OutcomeResult:
    stored: bool
    duplicate: bool
    orphan: bool


def _record(
    trx_id: str,
    callback_type: str,
    *,
    charging_status: str | None = None,
    charging_fail_reason: str | None = None,
    raw_payload: dict | None = None,
) -> OutcomeResult:
    with connection() as conn:
        orphan = not decisions_repo.exists_by_trx(conn, trx_id)
        inserted = outcomes_repo.insert_outcome(
            conn,
            trx_id=trx_id,
            callback_type=callback_type,
            charging_status=charging_status,
            charging_fail_reason=charging_fail_reason,
            raw_payload=raw_payload,
        )
    if orphan:
        _log.warning("orphan callback: type=%s trx_id=%s", callback_type, trx_id)
    # Mirror ke OLAP hanya untuk insert genuine (bukan duplikat) → tak ada dobel di OLAP.
    # Best-effort & loss-tolerant: kegagalan OLAP tak menggagalkan callback (ADR-014).
    if inserted:
        try:
            outcome_repo.write_outcome(
                trx_id=trx_id,
                callback_type=callback_type,
                charging_status=charging_status,
                charging_fail_reason=charging_fail_reason,
            )
        except Exception:  # noqa: BLE001 — OLAP loss-tolerant
            _log.warning("OLAP mirror outcome gagal: trx_id=%s", trx_id)
    return OutcomeResult(stored=True, duplicate=not inserted, orphan=orphan)


def record_subscription(cb: SubscriptionCallback) -> OutcomeResult:
    return _record(
        cb.trx_id,
        "subscription",
        charging_status=cb.charging_status,
        charging_fail_reason=cb.charging_fail_reason,
        raw_payload=cb.model_dump(mode="json"),
    )


def record_complaint(cb: ComplaintCallback) -> OutcomeResult:
    return _record(cb.trx_id, "complaint", raw_payload=cb.model_dump(mode="json"))
