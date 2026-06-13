"""Query analitik (`03 §7`): summary, timeseries, breakdown, search, decision-detail.

Sumber utama = OLAP ClickHouse `traffic_events` / `decision_log` (skala, dimensi device &
score_breakdown ditambahkan T-14). KPI charging (complaints / charging_fail_breakdown)
diambil dari OLTP `outcomes` dengan scoping berjenjang opsional via join ke `decisions`/
`services` (K4: charging terbatas tetapi tetap menghormati atribusi bila join tersedia).

Timezone (K2): agregat bucket dikonversi dari UTC via `toTimeZone(ts, tz)` lalu
`toStartOfHour/Day`, sehingga offset jam-bulat (mis. WIB +07) akurat.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import clickhouse_connect

from aegis.config import Settings, get_settings
from aegis.db.postgres import connection

_client = None

# dimension breakdown → kolom OLAP (allowlist; cegah injeksi nama kolom).
_DIM_COLUMN: dict[str, str] = {
    "service": "service",
    "campaign": "campaign",
    "source": "source",
    "pub_id": "pub_id",
    "country": "ip_country",
    "asn": "toString(ip_asn)",
    "decision": "decision",
    "weboptin_status": "weboptin_status",
    "webview": "toString(is_webview)",
    "browser": "browser",
    "device_brand": "device_brand",
    "device_model": "device_model",
    "os": "os",
}

# metric timeseries → agregat OLAP.
_METRIC_AGG: dict[str, str] = {
    "total": "count()",
    "allow": "countIf(decision = 'allow')",
    "block": "countIf(decision = 'block')",
    "weboptin_failed": "countIf(weboptin_status = 'failed')",
}


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


def _range(from_ts: datetime | None, to_ts: datetime | None) -> tuple[datetime, datetime]:
    lo = from_ts or datetime(1970, 1, 1, tzinfo=UTC)
    hi = to_ts or datetime.now(UTC)
    return _naive_utc(lo), _naive_utc(hi)


def _naive_utc(dt: datetime) -> datetime:
    """ClickHouse DateTime param butuh datetime naif (interpretasi UTC)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _scope(params: dict, *, service=None, campaign=None, source=None, pub_id=None) -> list[str]:
    """Klausa WHERE atribusi berjenjang OLAP (service→campaign→source→pub_id). Mutasi `params`."""
    clauses: list[str] = []
    if service:
        clauses.append("service = {service:String}")
        params["service"] = service
    if campaign:
        clauses.append("campaign = {campaign:String}")
        params["campaign"] = campaign
    if source:
        clauses.append("source = {source:String}")
        params["source"] = source
    if pub_id:
        clauses.append("pub_id = {pub_id:String}")
        params["pub_id"] = pub_id
    return clauses


def _decisions_scope(
    *, service=None, campaign=None, source=None, pub_id=None
) -> tuple[str, str, list]:
    """Scoping berjenjang OLTP via `decisions d`. -> (join_sql, where_extra, args_terurut).

    Argumen dikembalikan SESUAI URUTAN KEMUNCULAN di SQL: join (service, campaign) lebih dulu,
    lalu where_extra (source, pub_id). Pemanggil menyisipkan filter waktu di antara keduanya.
    """
    join, extra, join_args, extra_args = "", "", [], []
    if service:
        join += " JOIN services sv ON sv.id = d.service_id AND sv.slug = %s"
        join_args.append(service)
    if campaign:
        join += " JOIN campaigns cp ON cp.id = d.campaign_id AND cp.slug = %s"
        join_args.append(campaign)
    if source:
        extra += " AND d.source = %s"
        extra_args.append(source)
    if pub_id:
        extra += " AND d.pub_id = %s"
        extra_args.append(pub_id)
    return join, extra, (join_args, extra_args)


def _charging_kpis(
    from_ts: datetime, to_ts: datetime, *, service=None, campaign=None, source=None, pub_id=None
) -> tuple[int, dict[str, int]]:
    """complaints + charging_fail_breakdown dari OLTP outcomes (scoping berjenjang opsional)."""
    join, extra, (join_args, extra_args) = _decisions_scope(
        service=service, campaign=campaign, source=source, pub_id=pub_id
    )
    if join:  # outcomes butuh tautan ke decisions utk scoping
        join = " JOIN decisions d ON d.trx_id = o.trx_id" + join
    # Urutan args: join (service,campaign) → waktu (lo,hi) → extra (source,pub_id).
    args = [*join_args, from_ts, to_ts, *extra_args]
    base = "o.received_at >= %s AND o.received_at < %s" + extra
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"SELECT count(*) FROM outcomes o{join} "
            f"WHERE o.callback_type = 'complaint' AND {base}",
            args,
        )
        complaints = int(cur.fetchone()[0])
        cur.execute(
            f"SELECT o.charging_fail_reason, count(*) FROM outcomes o{join} "
            f"WHERE o.charging_status = 'failed' AND {base} "
            "GROUP BY o.charging_fail_reason",
            args,
        )
        breakdown = {(r[0] or "unknown"): int(r[1]) for r in cur.fetchall()}
    return complaints, breakdown


def _fraud_est(
    from_ts: datetime, to_ts: datetime, *, service=None, campaign=None, source=None, pub_id=None
) -> int:
    """fraud_est = Opsi B: trx allow + sinyal fraud terkonfirmasi (komplain / daily_limit /
    accepted-feedback robot). Scoping berjenjang via decisions. 0 saat cold-start."""
    join, extra, (join_args, extra_args) = _decisions_scope(
        service=service, campaign=campaign, source=source, pub_id=pub_id
    )
    args = [*join_args, from_ts, to_ts, *extra_args]
    sql = (
        "SELECT count(DISTINCT d.trx_id) FROM decisions d" + join + " WHERE d.decision = 'allow' "
        "AND d.created_at >= %s AND d.created_at < %s" + extra + " AND ("
        " EXISTS (SELECT 1 FROM outcomes o WHERE o.trx_id = d.trx_id AND "
        "  (o.callback_type = 'complaint' OR o.charging_fail_reason = 'daily_limit_reached'))"
        " OR EXISTS (SELECT 1 FROM feedback f WHERE f.trx_id = d.trx_id AND "
        "  f.review_status = 'accepted' AND f.flagged_label = 'robot'))"
    )
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, args)
        return int(cur.fetchone()[0])


def block_reasons(
    from_ts=None, to_ts=None, *, service=None, campaign=None, source=None, pub_id=None,
    limit: int = 10, settings: Settings | None = None,
) -> list[dict]:
    """Top-N alasan keputusan `block` + jumlahnya (OLTP `decisions`, sumber kebenaran reason).

    Scoping berjenjang via `_decisions_scope`. reason NULL/'' (mis. block via threshold tanpa
    hard-rule) dikelompokkan sebagai 'threshold'. Urut jumlah desc.
    """
    lo, hi = _range(from_ts, to_ts)
    join, extra, (join_args, extra_args) = _decisions_scope(
        service=service, campaign=campaign, source=source, pub_id=pub_id
    )
    args = [*join_args, lo, hi, *extra_args, int(limit)]
    sql = (
        "SELECT COALESCE(NULLIF(d.reason, ''), 'threshold') AS reason, count(*) AS n "
        "FROM decisions d" + join + " WHERE d.decision = 'block' "
        "AND d.created_at >= %s AND d.created_at < %s" + extra +
        " GROUP BY reason ORDER BY n DESC LIMIT %s"
    )
    with connection() as conn, conn.cursor() as cur:
        cur.execute(sql, args)
        return [{"reason": r[0], "count": int(r[1])} for r in cur.fetchall()]


# Metrik behavior (flattened, skew-free) di OLAP `traffic_events.features` (JSON dict).
# Hanya item interaksi user dgn pre-landing yang relevan & numerik.
_BEHAVIOR_METRICS: dict[str, str] = {
    "mouse_velocity_mean": "Rata-rata kecepatan mouse",
    "mouse_direction_changes": "Perubahan arah mouse",
    "scroll_depth_pct": "Kedalaman scroll (%)",
    "tap_count": "Jumlah tap",
    "interaction_count": "Jumlah interaksi",
    "time_to_cta_ms": "Waktu ke CTA (ms)",
}


def behavior_stats(
    from_ts=None, to_ts=None, *, service=None, campaign=None, source=None, pub_id=None,
    settings: Settings | None = None,
) -> list[dict]:
    """Rata-rata tiap metrik behavior yang tercatat (OLAP features). Hanya baris yg punya
    behavior (`has_mouse`/`interaction_count`>0 → diwakili `features != ''`). Scoping berjenjang."""
    s = settings or get_settings()
    lo, hi = _range(from_ts, to_ts)
    params: dict = {"lo": lo, "hi": hi}
    where = ["ts >= {lo:DateTime}", "ts < {hi:DateTime}", "features != ''", *_scope(
        params, service=service, campaign=campaign, source=source, pub_id=pub_id
    )]
    # avg(JSONExtractFloat(features, key)) + count baris (sampel) per metrik.
    selects = ", ".join(
        f"avg(JSONExtractFloat(features, '{k}')) AS avg_{i}" for i, k in enumerate(_BEHAVIOR_METRICS)
    )
    row = _get_client(s).query(
        f"SELECT count() AS sample, {selects} FROM traffic_events WHERE {' AND '.join(where)}",
        parameters=params,
    ).result_rows
    if not row:
        return []
    r = row[0]
    sample = int(r[0])
    out: list[dict] = []
    for i, (key, label) in enumerate(_BEHAVIOR_METRICS.items()):
        val = r[i + 1]
        out.append({
            "metric": key,
            "label": label,
            "avg": round(float(val), 3) if val is not None else 0.0,
            "sample": sample,
        })
    return out


def summary(
    from_ts=None, to_ts=None, *, service=None, campaign=None, source=None, pub_id=None,
    settings: Settings | None = None,
) -> dict:
    s = settings or get_settings()
    lo, hi = _range(from_ts, to_ts)
    params: dict = {"lo": lo, "hi": hi}
    where = ["ts >= {lo:DateTime}", "ts < {hi:DateTime}", *_scope(
        params, service=service, campaign=campaign, source=source, pub_id=pub_id
    )]
    row = _get_client(s).query(
        "SELECT count() AS total, "
        "countIf(decision = 'allow') AS allow, "
        "countIf(decision = 'block') AS block, "
        "countIf(weboptin_status = 'failed') AS weboptin_failed "
        f"FROM traffic_events WHERE {' AND '.join(where)}",
        parameters=params,
    ).result_rows
    total, allow, block, weboptin_failed = (row[0] if row else (0, 0, 0, 0))
    complaints, charging_fail = _charging_kpis(
        lo, hi, service=service, campaign=campaign, source=source, pub_id=pub_id
    )
    fraud_est = _fraud_est(
        lo, hi, service=service, campaign=campaign, source=source, pub_id=pub_id
    )
    return {
        "total": int(total),
        "allow": int(allow),
        "block": int(block),
        "weboptin_failed": int(weboptin_failed),
        "fraud_est": fraud_est,  # Opsi B: fraud lolos (sinyal terkonfirmasi)
        "complaints": complaints,
        "charging_fail_breakdown": charging_fail,
    }


def timeseries(
    metric: str, from_ts=None, to_ts=None, *, granularity="day", tz="UTC",
    service=None, campaign=None, source=None, pub_id=None, settings: Settings | None = None,
) -> list[dict]:
    if metric not in _METRIC_AGG:
        raise ValueError(f"metric tidak dikenal: {metric}")
    bucket_fn = "toStartOfHour" if granularity == "hour" else "toStartOfDay"
    s = settings or get_settings()
    lo, hi = _range(from_ts, to_ts)
    params: dict = {"lo": lo, "hi": hi, "tz": tz}
    where = ["ts >= {lo:DateTime}", "ts < {hi:DateTime}", *_scope(
        params, service=service, campaign=campaign, source=source, pub_id=pub_id
    )]
    rows = _get_client(s).query(
        f"SELECT {bucket_fn}(toTimeZone(ts, {{tz:String}})) AS bucket, "
        f"{_METRIC_AGG[metric]} AS value "
        f"FROM traffic_events WHERE {' AND '.join(where)} "
        "GROUP BY bucket ORDER BY bucket",
        parameters=params,
    ).result_rows
    return [{"bucket_ts": r[0], "value": float(r[1])} for r in rows]


def breakdown(
    dimension: str, from_ts=None, to_ts=None, *, tz="UTC",
    service=None, campaign=None, source=None, pub_id=None, limit=100,
    settings: Settings | None = None,
) -> list[dict]:
    col = _DIM_COLUMN.get(dimension)
    if col is None:
        raise ValueError(f"dimension tidak dikenal: {dimension}")
    s = settings or get_settings()
    lo, hi = _range(from_ts, to_ts)
    params: dict = {"lo": lo, "hi": hi, "lim": int(limit)}
    where = ["ts >= {lo:DateTime}", "ts < {hi:DateTime}", *_scope(
        params, service=service, campaign=campaign, source=source, pub_id=pub_id
    )]
    rows = _get_client(s).query(
        f"SELECT {col} AS key, count() AS cnt FROM traffic_events "
        f"WHERE {' AND '.join(where)} GROUP BY key ORDER BY cnt DESC LIMIT {{lim:UInt32}}",
        parameters=params,
    ).result_rows
    return [{"key": str(r[0]), "count": int(r[1])} for r in rows]


def _charging_trx_ids(charging_status: str, lo: datetime, hi: datetime) -> list[str]:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT trx_id FROM outcomes "
            "WHERE charging_status = %s AND received_at >= %s AND received_at < %s LIMIT 5000",
            (charging_status, lo, hi),
        )
        return [r[0] for r in cur.fetchall()]


def search(
    *, trx_id=None, device_id=None, decision=None, country=None, asn=None,
    service=None, campaign=None, source=None, pub_id=None, from_ts=None, to_ts=None,
    webview=None, browser=None, device_brand=None, device_model=None, os=None,
    charging_status=None, vpn=None, weboptin_status=None,
    limit=50, offset=0, settings: Settings | None = None,
) -> list[dict]:
    s = settings or get_settings()
    lo, hi = _range(from_ts, to_ts)
    params: dict = {"lo": lo, "hi": hi, "lim": int(limit), "off": int(offset)}
    where = ["ts >= {lo:DateTime}", "ts < {hi:DateTime}", *_scope(
        params, service=service, campaign=campaign, source=source, pub_id=pub_id
    )]

    def eq(col: str, name: str, val, typ="String"):
        where.append(f"{col} = {{{name}:{typ}}}")
        params[name] = val

    if trx_id:
        eq("trx_id", "trx_id", trx_id)
    if device_id:
        eq("device_id", "device_id", device_id)
    if decision:
        eq("decision", "decision", decision)
    if country:
        eq("ip_country", "country", country)
    if asn is not None:
        eq("ip_asn", "asn", int(asn), "UInt32")
    if browser:
        eq("browser", "browser", browser)
    if device_brand:
        eq("device_brand", "device_brand", device_brand)
    if device_model:
        eq("device_model", "device_model", device_model)
    if os:
        eq("os", "os", os)
    if weboptin_status:
        eq("weboptin_status", "weboptin_status", weboptin_status)
    if webview is not None:
        eq("is_webview", "webview", 1 if webview else 0, "UInt8")
    if vpn is not None:
        eq("vpn_proxy_tor", "vpn", 1 if vpn else 0, "UInt8")
    if charging_status:  # K4: filter charging via subset trx_id dari OLTP
        ids = _charging_trx_ids(charging_status, lo, hi)
        if not ids:
            return []
        where.append("trx_id IN {ctrx:Array(String)}")
        params["ctrx"] = ids

    rows = _get_client(s).query(
        "SELECT trx_id, device_id, service, source, pub_id, decision, weboptin_status, "
        "final_score, ts, campaign FROM traffic_events "
        f"WHERE {' AND '.join(where)} ORDER BY ts DESC LIMIT {{lim:UInt32}} OFFSET {{off:UInt32}}",
        parameters=params,
    ).result_rows
    return [
        {
            "trx_id": r[0], "device_id": r[1] or None, "service": r[2] or None,
            "campaign": r[9] or None,
            "source": r[3] or None, "pub_id": r[4] or None, "decision": r[5],
            "weboptin_status": r[6] or None, "final_score": float(r[7]), "ts": r[8],
        }
        for r in rows
    ]


def _oltp_decision(trx_id: str) -> dict | None:
    with connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT weboptin_host, rules_version, model_version, reason, threshold_used "
            "FROM decisions WHERE trx_id = %s",
            (trx_id,),
        )
        r = cur.fetchone()
        if r is None:
            return None
        return {
            "weboptin_host": r[0], "rules_version": r[1], "model_version": r[2],
            "reason": r[3], "threshold_used": float(r[4]) if r[4] is not None else None,
        }


def _outcomes(trx_id: str) -> list[dict]:
    from aegis.db.oltp import outcomes_repo

    with connection() as conn:
        return outcomes_repo.list_by_trx(conn, trx_id)


def decision_detail(trx_id: str, *, settings: Settings | None = None) -> dict | None:
    s = settings or get_settings()
    rows = _get_client(s).query(
        "SELECT trx_id, device_id, service, source, pub_id, decision, weboptin_status, "
        "final_score, signals, ip_country, ip_asn, ip_isp, connection_type, vpn_proxy_tor, "
        "ip_reputation, browser, os, device_type, device_brand, device_model, is_webview, "
        "score_breakdown, campaign FROM traffic_events WHERE trx_id = {trx:String} "
        "ORDER BY ts DESC LIMIT 1",
        parameters={"trx": trx_id},
    ).result_rows

    oltp = _oltp_decision(trx_id)
    if not rows and oltp is None:
        return None

    if rows:
        r = rows[0]
        breakdown_raw = json.loads(r[21]) if r[21] else {}
        detail = {
            "trx_id": r[0], "device_id": r[1] or None, "service": r[2] or None,
            "campaign": r[22] or None,
            "source": r[3] or None, "pub_id": r[4] or None, "decision": r[5],
            "weboptin_status": r[6] or None, "final_score": float(r[7]),
            "signals": json.loads(r[8]) if r[8] else {},
            "ip_intelligence": {
                "country": r[9] or None, "asn": int(r[10]) or None, "isp": r[11] or None,
                "connection_type": r[12] or None, "vpn_proxy_tor": bool(r[13]),
                "ip_reputation": r[14] or None,
            },
            "device_info": {
                "browser": r[15] or None, "os": r[16] or None, "device_type": r[17] or None,
                "brand": r[18] or None, "model": r[19] or None, "is_webview": bool(r[20]),
            },
            "score_breakdown": {
                "rules": breakdown_raw.get("rules"),
                "isolation_forest": breakdown_raw.get("isolation_forest"),
                "lightgbm": breakdown_raw.get("lightgbm"),
            },
        }
    else:  # OLAP hilang → detail minimal dari OLTP
        detail = {
            "trx_id": trx_id, "decision": "unknown", "final_score": None,
            "signals": {}, "ip_intelligence": {}, "device_info": {},
            "score_breakdown": {"rules": None, "isolation_forest": None, "lightgbm": None},
        }

    if oltp:
        detail["weboptin_host"] = oltp["weboptin_host"]
        detail["rules_version"] = oltp["rules_version"]
        detail["model_version"] = oltp["model_version"]
    detail["outcome"] = {
        "reason": (oltp or {}).get("reason"),
        "threshold_used": (oltp or {}).get("threshold_used"),
        "callbacks": _outcomes(trx_id),
    }
    return detail


def features_by_trx(
    trx_ids: list[str], *, settings: Settings | None = None
) -> dict[str, dict]:
    """Ambil fitur turunan (JSON) per-trx dari OLAP untuk retraining (T-17, skew-free).

    Bila satu trx punya >1 baris, ambil yang terbaru (argMax ts). Anti train/serve skew:
    fitur yang dipakai = fitur yang persis dihitung saat inference.
    """
    if not trx_ids:
        return {}
    s = settings or get_settings()
    rows = _get_client(s).query(
        "SELECT trx_id, argMax(features, ts) AS feat FROM traffic_events "
        "WHERE trx_id IN {trx:Array(String)} AND features != '' GROUP BY trx_id",
        parameters={"trx": trx_ids},
    ).result_rows
    return {r[0]: json.loads(r[1]) for r in rows if r[1]}


def recent_decisions(
    since: datetime | None = None, *, limit=20, settings: Settings | None = None
) -> list[dict]:
    """Feed keputusan terbaru untuk SSE (`/v1/stream`)."""
    s = settings or get_settings()
    params: dict = {"lim": int(limit)}
    where = ""
    if since is not None:
        where = "WHERE ts > {since:DateTime}"
        params["since"] = _naive_utc(since)
    rows = _get_client(s).query(
        "SELECT trx_id, device_id, service, source, pub_id, final_score, decision, "
        "weboptin_status, ts, campaign, reason "
        f"FROM decision_log {where} ORDER BY ts DESC LIMIT {{lim:UInt32}}",
        parameters=params,
    ).result_rows
    return [
        {
            "trx_id": r[0], "device_id": r[1] or None, "service": r[2] or None,
            "source": r[3] or None, "pub_id": r[4] or None, "final_score": float(r[5]),
            "decision": r[6], "weboptin_status": r[7] or None, "ts": r[8],
            "campaign": r[9] or None, "reason": r[10] or None,
        }
        for r in rows
    ]
