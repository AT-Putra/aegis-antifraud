"""Logging JSON terstruktur + audit trail aksi admin (T-18, TRD §7).

Audit keputusan = tabel `decisions` (immutable, ber-versi config+model). Audit AKSI admin
(ubah config, aktivasi model, CRUD user/service/campaign) dicatat sebagai log JSON
(logger `aegis.audit`, field `audit=true`).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for k, v in getattr(record, "extra_fields", {}).items():
            payload[k] = v
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


_audit_log = logging.getLogger("aegis.audit")


def audit(action: str, actor: str | None = None, **fields: object) -> None:
    """Catat aksi admin ke audit trail (log JSON)."""
    _audit_log.info(
        action,
        extra={"extra_fields": {"audit": True, "action": action, "actor": actor, **fields}},
    )
