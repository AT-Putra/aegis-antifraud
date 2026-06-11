"""Tulis event ke ClickHouse (OLAP). async_insert: batch server-side, low-latency (K4).

OLAP loss-tolerant (analitik); sumber kebenaran = decisions OLTP.
"""

from __future__ import annotations

import json

import clickhouse_connect

from aegis.config import Settings, get_settings

_ASYNC = {"async_insert": 1, "wait_for_async_insert": 0}
_client = None


def _get_client(s: Settings):
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=s.clickhouse_host,
            port=s.clickhouse_port,
            username=s.clickhouse_user,
            password=s.clickhouse_password,
            database=s.clickhouse_db,
        )
    return _client


def write_event(
    *,
    trx_id: str,
    device_id: str,
    service: str | None,
    source: str | None,
    pub_id: str | None,
    signals: dict,
    features: dict,
    ip_intel: dict,
    decision: str,
    final_score: float | None,
    weboptin_status: str,
    rules_version: int | None,
    model_version: int | None,
    settings: Settings | None = None,
) -> None:
    s = settings or get_settings()
    client = _get_client(s)
    client.insert(
        "traffic_events",
        [[
            trx_id, device_id, service or "", source or "", pub_id or "",
            json.dumps(signals, default=str), json.dumps(features, default=str),
            ip_intel.get("country") or "", int(ip_intel.get("asn") or 0),
            ip_intel.get("isp") or "", ip_intel.get("connection_type") or "",
            1 if ip_intel.get("vpn_proxy_tor") else 0, ip_intel.get("ip_reputation") or "",
            decision, float(final_score or 0.0), weboptin_status,
        ]],
        column_names=[
            "trx_id", "device_id", "service", "source", "pub_id", "signals", "features",
            "ip_country", "ip_asn", "ip_isp", "connection_type", "vpn_proxy_tor",
            "ip_reputation", "decision", "final_score", "weboptin_status",
        ],
        settings=_ASYNC,
    )
    client.insert(
        "decision_log",
        [[
            trx_id, device_id, service or "", source or "", pub_id or "",
            float(final_score or 0.0), decision, weboptin_status,
            int(rules_version or 0), int(model_version or 0),
        ]],
        column_names=[
            "trx_id", "device_id", "service", "source", "pub_id", "final_score",
            "decision", "weboptin_status", "rules_version", "model_version",
        ],
        settings=_ASYNC,
    )
