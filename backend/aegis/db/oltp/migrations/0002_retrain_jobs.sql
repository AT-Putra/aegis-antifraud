-- T-15: pencatatan job retraining (trigger admin → status). Eksekusi worker = T-17.
-- Idempoten (IF NOT EXISTS). status: queued → running → done|failed.

CREATE TABLE IF NOT EXISTS retrain_jobs (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    status       text NOT NULL DEFAULT 'queued'
                 CHECK (status IN ('queued', 'running', 'done', 'failed')),
    metrics      jsonb,
    requested_by uuid REFERENCES users(id),
    created_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz
);

CREATE INDEX IF NOT EXISTS idx_retrain_jobs_created ON retrain_jobs(created_at);
