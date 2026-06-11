-- Aegis OLTP skema awal (T-02, TRD §4.1). Idempoten (IF NOT EXISTS).
-- Keamanan: hmac_secret = ciphertext (BYTEA), bukan plaintext (TQ-08);
-- password_hash = argon2 (diisi T-03/T-15); enum via CHECK; FK menjaga relasi.

CREATE TABLE IF NOT EXISTS users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username      text NOT NULL UNIQUE,
    password_hash text NOT NULL,
    role          text NOT NULL CHECK (role IN ('admin', 'user')),
    timezone      text NOT NULL DEFAULT 'Asia/Jakarta',
    active        boolean NOT NULL DEFAULT true,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app_settings (
    key        text PRIMARY KEY,
    value      text NOT NULL,
    updated_by uuid REFERENCES users(id),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS services (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{1,64}$'),
    name        text NOT NULL,
    operator    text,
    cp_api_url  text NOT NULL CHECK (cp_api_url LIKE 'https://%'),
    hmac_secret bytea NOT NULL,                       -- AES-256-GCM ciphertext (TQ-08)
    status      text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS devices (
    device_id          text PRIMARY KEY,
    fingerprint_hash   text NOT NULL,
    components_summary jsonb,
    first_seen         timestamptz NOT NULL DEFAULT now(),
    last_seen          timestamptz NOT NULL DEFAULT now(),
    event_count        bigint NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS rule_configs (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version             integer NOT NULL UNIQUE,
    params              jsonb NOT NULL DEFAULT '{}'::jsonb,
    defaults_range_meta jsonb NOT NULL DEFAULT '{}'::jsonb,
    blend_weights       jsonb NOT NULL DEFAULT '{}'::jsonb,
    threshold           double precision NOT NULL DEFAULT 0.5,
    active              boolean NOT NULL DEFAULT false,
    created_by          uuid REFERENCES users(id),
    created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS model_versions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    version         integer NOT NULL UNIQUE,
    algorithm       text NOT NULL,
    artifact_ref    text,
    calibration_ref text,
    trained_at      timestamptz,
    metrics         jsonb NOT NULL DEFAULT '{}'::jsonb,
    active          boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS decisions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    trx_id          varchar(128) NOT NULL UNIQUE,
    device_id       text REFERENCES devices(device_id),
    service_id      uuid REFERENCES services(id),
    source          varchar(64),
    pub_id          varchar(64),
    final_score     double precision,
    decision        text NOT NULL CHECK (decision IN ('allow', 'block')),
    threshold_used  double precision,
    rules_version   integer REFERENCES rule_configs(version),
    model_version   integer REFERENCES model_versions(version),
    reason          text,
    weboptin_status text NOT NULL DEFAULT 'na' CHECK (weboptin_status IN ('minted', 'failed', 'na')),
    weboptin_host   text,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_decisions_device  ON decisions(device_id);
CREATE INDEX IF NOT EXISTS idx_decisions_service ON decisions(service_id);
CREATE INDEX IF NOT EXISTS idx_decisions_attr    ON decisions(service_id, source, pub_id);
CREATE INDEX IF NOT EXISTS idx_decisions_created ON decisions(created_at);

CREATE TABLE IF NOT EXISTS outcomes (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    trx_id               varchar(128) NOT NULL,
    callback_type        text NOT NULL CHECK (callback_type IN ('subscription', 'complaint')),
    charging_status      text CHECK (charging_status IN ('success', 'failed')),
    charging_fail_reason text CHECK (charging_fail_reason IN ('insufficient_balance', 'daily_limit_reached')),
    received_at          timestamptz NOT NULL DEFAULT now(),
    raw_payload          jsonb,
    CONSTRAINT uq_outcome UNIQUE (callback_type, trx_id)   -- idempotensi (event, trx_id)
);

CREATE INDEX IF NOT EXISTS idx_outcomes_trx ON outcomes(trx_id);

CREATE TABLE IF NOT EXISTS feedback (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    trx_id        varchar(128),
    decision_id   uuid REFERENCES decisions(id),
    user_id       uuid REFERENCES users(id),
    flagged_label text NOT NULL CHECK (flagged_label IN ('human', 'robot')),
    note          text,
    review_status text NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending', 'accepted', 'rejected')),
    reviewed_by   uuid REFERENCES users(id),
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(review_status);
