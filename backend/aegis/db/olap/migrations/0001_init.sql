-- Aegis OLAP skema awal (T-02, TRD §4.2). ClickHouse MergeTree.
-- Retensi event mentah >= 2 tahun (ADR), partisi bulanan; dimensi service/source/pub_id.

CREATE TABLE IF NOT EXISTS traffic_events (
    event_id        UUID DEFAULT generateUUIDv4(),
    trx_id          String,
    device_id       String,
    service         String,
    source          String,
    pub_id          String,
    ts              DateTime DEFAULT now(),
    signals         String,            -- JSON sinyal fingerprint+behavior (flattened di query)
    features        String,            -- JSON fitur turunan (cegah skew: dihitung di features/)
    ip_country      String,
    ip_asn          UInt32,
    ip_isp          String,
    connection_type String,
    vpn_proxy_tor   UInt8,
    ip_reputation   String,
    decision        String,
    final_score     Float64,
    weboptin_status String
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (ts, service, device_id)
TTL ts + INTERVAL 2 YEAR;

CREATE TABLE IF NOT EXISTS decision_log (
    trx_id          String,
    device_id       String,
    service         String,
    source          String,
    pub_id          String,
    final_score     Float64,
    decision        String,
    weboptin_status String,
    rules_version   UInt32,
    model_version   UInt32,
    ts              DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (ts, service);
