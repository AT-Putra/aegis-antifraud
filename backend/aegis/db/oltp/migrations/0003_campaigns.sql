-- T-21 (F-16): registry campaign = pre-landing portabel. Idempoten.
-- 1 pre-landing = 1 campaign, milik 1 service; allowed_origins = whitelist CORS per-campaign.

CREATE TABLE IF NOT EXISTS campaigns (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]{1,64}$'),
    name            text NOT NULL,
    service_id      uuid NOT NULL REFERENCES services(id),
    allowed_origins text[] NOT NULL DEFAULT '{}',
    status          text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_service ON campaigns(service_id);

-- Atribusi berjenjang service→campaign→source→pub_id: decisions menautkan campaign.
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS campaign_id uuid REFERENCES campaigns(id);
