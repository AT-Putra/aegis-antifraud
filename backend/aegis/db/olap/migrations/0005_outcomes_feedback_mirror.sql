-- Mirror outcomes (callback billing) & feedback (review) ke OLAP untuk statistik full-OLAP
-- (kebijakan 2026-06-13, ADR-014). Sumber kebenaran tetap OLTP; ini cermin loss-tolerant
-- agar agregat fraud_est/complaints/charging lepas dari jalur tulis panas. Idempoten.
-- Scoping berjenjang dicapai via JOIN/IN ke traffic_events (punya service/campaign/source/pub_id)
-- lewat trx_id; tabel mirror cukup menyimpan field inti.

-- outcome_log: cermin OLTP outcomes. uq OLTP = (callback_type, trx_id) → dedup via ORDER BY.
CREATE TABLE IF NOT EXISTS outcome_log (
    trx_id               String,
    callback_type        String,            -- 'subscription' | 'complaint'
    charging_status      String,            -- 'success' | 'failed' | ''
    charging_fail_reason String,            -- 'insufficient_balance' | 'daily_limit_reached' | ''
    received_at          DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree
PARTITION BY toYYYYMM(received_at)
ORDER BY (trx_id, callback_type)
TTL received_at + INTERVAL 2 YEAR;

-- feedback_log: cermin OLTP feedback (hanya yang sudah di-review). review mengubah status →
-- ReplacingMergeTree(version): versi terbaru (timestamp) menang.
CREATE TABLE IF NOT EXISTS feedback_log (
    id            String,
    trx_id        String,
    flagged_label String,            -- 'human' | 'robot'
    review_status String,            -- 'accepted' | 'rejected'
    created_at    DateTime DEFAULT now(),
    version       UInt64
)
ENGINE = ReplacingMergeTree(version)
PARTITION BY toYYYYMM(created_at)
ORDER BY id
TTL created_at + INTERVAL 2 YEAR;
