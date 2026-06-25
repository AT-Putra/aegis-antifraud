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
from datetime import UTC, datetime, timedelta

import clickhouse_connect
from clickhouse_connect.driver import httputil

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
            # Endpoint sync FastAPI jalan di thread-pool → dashboard menembak banyak query
            # analitik paralel pada satu klien bersama. Session ClickHouse melarang query
            # konkuren dalam satu session ("Attempt to execute concurrent queries within the
            # same session"). Query kita murni agregasi stateless → matikan session id agar
            # tiap query = request HTTP independen (aman konkuren).
            autogenerate_session_id=False,
            # Dashboard menembak ~10 query analitik paralel pada klien bersama ini; pool
            # urllib3 default (maxsize=8) penuh saat burst → urllib3 WARNING "Connection
            # pool is full" + koneksi ekstra dibuka lalu dibuang (tak di-reuse). Naikkan
            # maxsize ke 16 (≥ jumlah query paralel) agar koneksi keep-alive dipakai ulang.
            pool_mgr=httputil.get_pool_manager(maxsize=16),
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


# Horizon mundur saat cek "trx dikenal Aegis" utk mengecualikan outcome ORPHAN (ADR-023):
# trx harus ada di traffic_events dalam [awal_window − N hari, akhir_window]. N=30 menutup
# semua latency callback realistis (billing final/no-retry) sekaligus mem-prune partisi bulanan.
_OUTCOME_KNOWN_HORIZON_DAYS = 30


def _known_trx_subquery(params: dict, *, lo, hi, service, campaign, source, pub_id) -> str:
    """Subquery trx_id 'DIKENAL Aegis' dari `traffic_events` (ada = pernah di-scoring Aegis).

    Dipakai utk meng-`IN`-kan mirror outcome_log → (a) mengecualikan ORPHAN (trx tak pernah lewat
    Aegis, mis. postback channel lain) dari agregat — ADR-023/T-31; (b) scoping berjenjang full-OLAP
    tanpa join OLTP (ADR-014). Window keberadaan = [lo − 30 hari, hi] agar callback sah yang
    telat/lintas tengah malam tetap terhitung. Pakai param `lo_known` (JANGAN timpa `lo`
    outcome-window yang dipakai filter `received_at`).
    """
    params["lo_known"] = lo - timedelta(days=_OUTCOME_KNOWN_HORIZON_DAYS)
    params["hi"] = hi
    where = ["ts >= {lo_known:DateTime}", "ts < {hi:DateTime}", *_scope(
        params, service=service, campaign=campaign, source=source, pub_id=pub_id
    )]
    return f"SELECT trx_id FROM traffic_events WHERE {' AND '.join(where)}"


def _charging_kpis(
    from_ts: datetime, to_ts: datetime, *, service=None, campaign=None, source=None, pub_id=None,
    settings: Settings | None = None,
) -> tuple[int, dict[str, int]]:
    """complaints + charging_fail_breakdown dari OLAP `outcome_log` (full-OLAP, scoping berjenjang).

    Scoping: outcome di-`IN`-kan ke trx_id traffic_events ber-scope (window pada ts traffic).
    """
    s = settings or get_settings()
    client = _get_client(s)
    lo, hi = _range(from_ts, to_ts)
    p: dict = {"lo": lo, "hi": hi}
    # Filter received_at outcome pada window; trx HARUS dikenal Aegis (buang ORPHAN, ADR-023) —
    # known-trx subquery SELALU diterapkan (+ scope bila ada).
    sub = _known_trx_subquery(p, lo=lo, hi=hi, service=service, campaign=campaign,
                              source=source, pub_id=pub_id)
    in_clause = f" AND trx_id IN ({sub})"
    # count(DISTINCT trx_id): uq OLTP = (callback_type,trx_id) → tahan duplikat pra-merge
    # ReplacingMergeTree tanpa perlu FINAL.
    complaints = int(client.query(
        "SELECT count(DISTINCT trx_id) FROM outcome_log "
        "WHERE callback_type = 'complaint' AND received_at >= {lo:DateTime} "
        f"AND received_at < {{hi:DateTime}}{in_clause}",
        parameters=p,
    ).result_rows[0][0])
    rows = client.query(
        "SELECT if(charging_fail_reason = '', 'unknown', charging_fail_reason) AS r, "
        "count(DISTINCT trx_id) FROM outcome_log "
        "WHERE charging_status = 'failed' AND received_at >= {lo:DateTime} "
        f"AND received_at < {{hi:DateTime}}{in_clause} GROUP BY r",
        parameters=p,
    ).result_rows
    breakdown = {str(r[0]): int(r[1]) for r in rows}
    return complaints, breakdown


def charging_funnel(
    from_ts=None, to_ts=None, *, service=None, campaign=None, source=None, pub_id=None,
    settings: Settings | None = None,
) -> dict:
    """Funnel outcome langganan dari OLAP `outcome_log` (full-OLAP, scoping berjenjang, T-30).

    registration_success = callback subscription (SubscriptionCallback HANYA dikirim saat
    langganan sukses); charging_success/failed = subset charging_status; breakdown gagal =
    insufficient_balance | daily_limit_reached | other (reason ''). complaints = callback
    complaint. `uniqExact(trx_id)` agar tahan duplikat pra-merge (uq OLTP = (callback_type,
    trx_id)) tanpa `FINAL`. Window pada received_at; scoping via trx IN traffic ber-scope.
    """
    s = settings or get_settings()
    client = _get_client(s)
    lo, hi = _range(from_ts, to_ts)
    p: dict = {"lo": lo, "hi": hi}
    # trx HARUS dikenal Aegis (buang ORPHAN, ADR-023) — known-trx SELALU (+ scope bila ada).
    sub = _known_trx_subquery(p, lo=lo, hi=hi, service=service, campaign=campaign,
                              source=source, pub_id=pub_id)
    in_clause = f" AND trx_id IN ({sub})"
    win = ("callback_type = 'subscription' AND received_at >= {lo:DateTime} "
           f"AND received_at < {{hi:DateTime}}{in_clause}")
    row = client.query(
        "SELECT uniqExact(trx_id) AS reg, "
        "uniqExactIf(trx_id, charging_status = 'success') AS ok, "
        "uniqExactIf(trx_id, charging_status = 'failed') AS fail, "
        "uniqExactIf(trx_id, charging_status = 'failed' AND "
        "  charging_fail_reason = 'insufficient_balance') AS insuf, "
        "uniqExactIf(trx_id, charging_status = 'failed' AND "
        "  charging_fail_reason = 'daily_limit_reached') AS dlimit, "
        "uniqExactIf(trx_id, charging_status = 'failed' AND "
        "  charging_fail_reason NOT IN ('insufficient_balance', 'daily_limit_reached')) AS other "
        f"FROM outcome_log WHERE {win}",
        parameters=p,
    ).result_rows
    reg, ok, fail, insuf, dlimit, other = (row[0] if row else (0, 0, 0, 0, 0, 0))
    complaints = int(client.query(
        "SELECT uniqExact(trx_id) FROM outcome_log "
        "WHERE callback_type = 'complaint' AND received_at >= {lo:DateTime} "
        f"AND received_at < {{hi:DateTime}}{in_clause}",
        parameters=p,
    ).result_rows[0][0])
    return {
        "registration_success": int(reg),
        "charging_success": int(ok),
        "charging_failed": int(fail),
        "charging_fail_breakdown": {
            "insufficient_balance": int(insuf),
            "daily_limit_reached": int(dlimit),
            "other": int(other),
        },
        "complaints": complaints,
    }


def _fraud_est(
    from_ts: datetime, to_ts: datetime, *, service=None, campaign=None, source=None, pub_id=None,
    settings: Settings | None = None,
) -> int:
    """fraud_est = Opsi B: trx allow + sinyal fraud terkonfirmasi (komplain / daily_limit /
    accepted-feedback robot). Full-OLAP: traffic_events + outcome_log + feedback_log. Cold→0."""
    s = settings or get_settings()
    client = _get_client(s)
    lo, hi = _range(from_ts, to_ts)
    p: dict = {"lo": lo, "hi": hi}
    where = ["ts >= {lo:DateTime}", "ts < {hi:DateTime}", "decision = 'allow'", *_scope(
        p, service=service, campaign=campaign, source=source, pub_id=pub_id
    )]
    # trx allow ber-scope yang punya sinyal fraud terkonfirmasi di mirror OLAP.
    sql = (
        "SELECT count(DISTINCT trx_id) FROM traffic_events "
        f"WHERE {' AND '.join(where)} AND ("
        " trx_id IN (SELECT trx_id FROM outcome_log WHERE callback_type = 'complaint' "
        "  OR charging_fail_reason = 'daily_limit_reached')"
        " OR trx_id IN (SELECT trx_id FROM feedback_log FINAL "
        "  WHERE review_status = 'accepted' AND flagged_label = 'robot'))"
    )
    return int(client.query(sql, parameters=p).result_rows[0][0])


def block_reasons(
    from_ts=None, to_ts=None, *, service=None, campaign=None, source=None, pub_id=None,
    limit: int = 10, settings: Settings | None = None,
) -> list[dict]:
    """Top-N alasan keputusan `block` + jumlahnya (OLAP `decision_log`, full-OLAP statistik).

    Scoping berjenjang via `_scope` (sama spt summary/breakdown). reason kosong (mis. block
    via threshold tanpa hard-rule, atau baris sebelum migrasi `0004`) dikelompokkan sebagai
    'threshold'. Urut jumlah desc. *Trade-off:* `reason` OLAP loss-tolerant (async insert);
    untuk statistik agregat dapat diterima.
    """
    s = settings or get_settings()
    lo, hi = _range(from_ts, to_ts)
    params: dict = {"lo": lo, "hi": hi, "lim": int(limit)}
    where = ["ts >= {lo:DateTime}", "ts < {hi:DateTime}", "decision = 'block'", *_scope(
        params, service=service, campaign=campaign, source=source, pub_id=pub_id
    )]
    rows = _get_client(s).query(
        "SELECT if(reason = '', 'threshold', reason) AS reason, count() AS n "
        f"FROM decision_log WHERE {' AND '.join(where)} "
        "GROUP BY reason ORDER BY n DESC LIMIT {lim:UInt32}",
        parameters=params,
    ).result_rows
    return [{"reason": str(r[0]), "count": int(r[1])} for r in rows]


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
        f"avg(JSONExtractFloat(features, '{k}')) AS avg_{i}"
        for i, k in enumerate(_BEHAVIOR_METRICS)
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
    # Format bucket sbg STRING wall-time naif di `tz` (bukan DateTime) — cegah clickhouse-connect
    # menormalkan DateTime('tz') kembali ke UTC di kabel (bug chart tampil UTC). Frontend
    # `formatBucket` memaknai string naif ini sbg wall-time tz apa adanya (ADR-017).
    rows = _get_client(s).query(
        f"SELECT formatDateTime({bucket_fn}(toTimeZone(ts, {{tz:String}})), "
        f"'%Y-%m-%dT%H:%i:%S') AS bucket, "  # %i=menit (ClickHouse); %M=nama bulan!
        f"{_METRIC_AGG[metric]} AS value "
        f"FROM traffic_events WHERE {' AND '.join(where)} "
        "GROUP BY bucket ORDER BY bucket",
        parameters=params,
    ).result_rows
    return [{"bucket_ts": str(r[0]), "value": float(r[1])} for r in rows]


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


def _outcome_trx_ids(
    lo: datetime, hi: datetime, *, subscription: bool = False,
    charging_status: str | None = None, charging_fail_reason: str | None = None,
    settings: Settings | None = None,
) -> list[str]:
    """trx_id outcome langganan dari OLAP `outcome_log` (full-OLAP, filter search berjenjang T-27).

    - subscription=True → hanya callback_type='subscription' (punya outcome langganan).
    - charging_status → 'success' | 'failed'.
    - charging_fail_reason → 'insufficient_balance' | 'daily_limit_reached' | 'other'
      ('other' = gagal tanpa reason spesifik → charging_status='failed' & reason kosong).
    """
    s = settings or get_settings()
    conds = ["received_at >= {lo:DateTime}", "received_at < {hi:DateTime}"]
    params: dict = {"lo": lo, "hi": hi}
    if subscription:
        conds.append("callback_type = {ct:String}")
        params["ct"] = "subscription"
    if charging_status:
        conds.append("charging_status = {cs:String}")
        params["cs"] = charging_status
    if charging_fail_reason:
        if charging_fail_reason == "other":
            conds.append("charging_status = 'failed'")
            conds.append("charging_fail_reason = ''")
        else:
            conds.append("charging_fail_reason = {cfr:String}")
            params["cfr"] = charging_fail_reason
    rows = _get_client(s).query(
        "SELECT DISTINCT trx_id FROM outcome_log "
        f"WHERE {' AND '.join(conds)} LIMIT 5000",
        parameters=params,
    ).result_rows
    return [r[0] for r in rows]


def distinct_countries(*, settings: Settings | None = None) -> list[str]:
    """Negara (ISO ip_country) yang pernah muncul di OLAP `traffic_events`, urut alfabetis.

    Untuk dropdown filter Pencarian (T-27) — selaras pola registry service/campaign.
    """
    s = settings or get_settings()
    rows = _get_client(s).query(
        "SELECT DISTINCT ip_country FROM traffic_events "
        "WHERE ip_country != '' ORDER BY ip_country LIMIT 1000"
    ).result_rows
    return [r[0] for r in rows]


def search(
    *, trx_id=None, device_id=None, decision=None, country=None, asn=None,
    service=None, campaign=None, source=None, pub_id=None, from_ts=None, to_ts=None,
    webview=None, browser=None, device_brand=None, device_model=None, os=None,
    charging_status=None, vpn=None, weboptin_status=None,
    subscribed=None, charging_fail_reason=None,
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
    # Filter outcome langganan berjenjang (T-27): subscribed→charging_status→charging_fail_reason.
    # Semua via subset trx_id dari OLAP outcome_log (full-OLAP).
    if subscribed or charging_status or charging_fail_reason:
        ids = _outcome_trx_ids(
            lo, hi, subscription=bool(subscribed),
            charging_status=charging_status, charging_fail_reason=charging_fail_reason,
        )
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


def _config_by_version(version: int | None) -> dict | None:
    """Config rules HISTORIS by versi (penjelasan setia ke saat keputusan dibuat)."""
    if version is None:
        return None
    from aegis.db.oltp import rule_configs_repo

    with connection() as conn:
        return rule_configs_repo.get_by_version(conn, version)


def _recompute_features(signals_raw: dict, ip_stored: dict) -> tuple[dict, list[str]]:
    """Rekonstruksi best-effort fitur dari `signals` saat OLAP `features` kosong.

    Terdegradasi: `ip_is_datacenter` tak presisi (didekati dari connection_type) & device
    history hilang → kembalikan warnings agar UI jujur.
    """
    from aegis.features.extract import extract_features
    from aegis.features.schema import FeatureInput
    from aegis.schemas.scoring import Signals

    warnings: list[str] = []
    conn_type = (ip_stored.get("connection_type") or "").lower()
    ip_intel = {
        "vpn_proxy_tor": bool(ip_stored.get("vpn_proxy_tor")),
        "is_datacenter": conn_type in ("hosting", "datacenter"),
        "is_mobile_carrier": conn_type == "mobile",
        "ip_reputation": ip_stored.get("ip_reputation"),
    }
    warnings.append(
        "Fitur direkonstruksi dari signals (OLAP features kosong); "
        "ip_is_datacenter didekati dari connection_type, device history tak tersedia."
    )
    feature_input = FeatureInput(
        signals=Signals.model_validate(signals_raw),
        ip_intel=ip_intel,
        device_info=None,
        device_history={},
    )
    return extract_features(feature_input), warnings


def _attach_explainability(
    detail: dict, *, features_raw: dict, oltp: dict | None
) -> None:
    """Susun & lampirkan `detail["explainability"]` (03 §7). Degradasi anggun → available:false.

    Tak pernah menggagalkan endpoint detail: bila apa pun gagal, set available:false.
    """
    from aegis.scoring.explain import build_decision_explainability

    try:
        rules_version = (oltp or {}).get("rules_version")
        cfg = _config_by_version(rules_version)
        params = (cfg or {}).get("params") or {}
        blend_weights = (cfg or {}).get("blend_weights") or {}
        threshold = (
            float(cfg["threshold"]) if cfg and cfg.get("threshold") is not None
            else (oltp or {}).get("threshold_used")
        )
        if threshold is None:
            detail["explainability"] = {"available": False, "version": "1",
                                        "feature_source": "unavailable", "warnings": [],
                                        "rules_version_used": rules_version}
            return

        warnings: list[str] = []
        if features_raw:
            features = features_raw
            feature_source = "stored_features"
        else:
            features, warnings = _recompute_features(detail.get("signals") or {},
                                                      detail.get("ip_intelligence") or {})
            feature_source = "recomputed_from_signals"

        detail["explainability"] = build_decision_explainability(
            features,
            params=params,
            score_breakdown=detail.get("score_breakdown") or {},
            blend_weights=blend_weights,
            final_score=detail.get("final_score"),
            threshold=float(threshold),
            decision=detail.get("decision", "unknown"),
            reason=(detail.get("outcome") or {}).get("reason"),
            feature_source=feature_source,
            rules_version_used=rules_version,
            warnings=warnings,
        )
    except Exception:
        detail["explainability"] = {"available": False, "version": "1",
                                    "feature_source": "unavailable", "warnings": []}


def decision_detail(trx_id: str, *, settings: Settings | None = None) -> dict | None:
    s = settings or get_settings()
    rows = _get_client(s).query(
        "SELECT trx_id, device_id, service, source, pub_id, decision, weboptin_status, "
        "final_score, signals, ip_country, ip_asn, ip_isp, connection_type, vpn_proxy_tor, "
        "ip_reputation, browser, os, device_type, device_brand, device_model, is_webview, "
        "score_breakdown, campaign, features, ip_address "
        "FROM traffic_events WHERE trx_id = {trx:String} "
        "ORDER BY ts DESC LIMIT 1",
        parameters={"trx": trx_id},
    ).result_rows

    oltp = _oltp_decision(trx_id)
    if not rows and oltp is None:
        return None

    if rows:
        r = rows[0]
        breakdown_raw = json.loads(r[21]) if r[21] else {}
        features_raw = json.loads(r[23]) if r[23] else {}
        detail = {
            "trx_id": r[0], "device_id": r[1] or None, "service": r[2] or None,
            "campaign": r[22] or None,
            "source": r[3] or None, "pub_id": r[4] or None, "decision": r[5],
            "weboptin_status": r[6] or None, "final_score": float(r[7]),
            "signals": json.loads(r[8]) if r[8] else {},
            "ip_intelligence": {
                "ip_address": r[24] or None,
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
        features_raw = {}
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
    _attach_explainability(detail, features_raw=features_raw, oltp=oltp)
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


def _parse_breakdown(raw: str | None) -> dict:
    """Normalkan score_breakdown JSON → 3 kunci tetap (rules/IF/LGBM), nilai float|None.

    Baris decision_log lama (sebelum migrasi 0006) → kolom kosong → semua null.
    """
    b = json.loads(raw) if raw else {}
    return {
        "rules": b.get("rules"),
        "isolation_forest": b.get("isolation_forest"),
        "lightgbm": b.get("lightgbm"),
    }


def recent_decisions(
    since: datetime | None = None,
    *,
    to: datetime | None = None,
    limit=20,
    service: str | None = None,
    campaign: str | None = None,
    source: str | None = None,
    pub_id: str | None = None,
    settings: Settings | None = None,
) -> list[dict]:
    """Feed keputusan terbaru. Dua mode (ADR-022):
    - **SSE live** (`/v1/stream`): `since`=watermark `ts` terakhir → ambil yang lebih baru.
    - **Snapshot beku** (`/v1/analytics/recent`): `since`=from + `to` → rentang historis statis.

    Scope berjenjang (service→campaign→source→pub_id) menyaring feed (sebelumnya diabaikan).
    """
    s = settings or get_settings()
    params: dict = {"lim": int(limit)}
    clauses: list[str] = []
    if since is not None:
        clauses.append("ts > {since:DateTime}")
        params["since"] = _naive_utc(since)
    if to is not None:
        clauses.append("ts <= {to:DateTime}")
        params["to"] = _naive_utc(to)
    clauses += _scope(params, service=service, campaign=campaign, source=source, pub_id=pub_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = _get_client(s).query(
        "SELECT trx_id, device_id, service, source, pub_id, final_score, decision, "
        "weboptin_status, ts, campaign, reason, score_breakdown "
        f"FROM decision_log {where} ORDER BY ts DESC LIMIT {{lim:UInt32}}",
        parameters=params,
    ).result_rows
    return [
        {
            "trx_id": r[0], "device_id": r[1] or None, "service": r[2] or None,
            "source": r[3] or None, "pub_id": r[4] or None, "final_score": float(r[5]),
            "decision": r[6], "weboptin_status": r[7] or None, "ts": r[8],
            "campaign": r[9] or None, "reason": r[10] or None,
            "score_breakdown": _parse_breakdown(r[11]),
        }
        for r in rows
    ]
