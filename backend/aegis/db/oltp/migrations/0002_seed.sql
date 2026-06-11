-- Seed minimal (T-02). Idempoten via ON CONFLICT.
-- Admin user awal SENGAJA tidak di-seed di sini (butuh hashing argon2 dari T-03;
-- dibuat via bootstrap saat T-15).

INSERT INTO app_settings (key, value)
VALUES ('default_timezone', 'Asia/Jakarta')
ON CONFLICT (key) DO NOTHING;

-- rule_configs v1 PLACEHOLDER agar scoring dapat boot saat cold-start.
-- Bobot blend: rules-only dulu (IF/LGBM = 0 sampai model tersedia).
-- threshold/params final ditetapkan saat tuning (TRD TQ-02) — JANGAN dianggap optimal.
INSERT INTO rule_configs (version, params, defaults_range_meta, blend_weights, threshold, active)
VALUES (
    1,
    '{}'::jsonb,
    '{}'::jsonb,
    '{"rules": 1.0, "isolation_forest": 0.0, "lightgbm": 0.0}'::jsonb,
    0.5,
    true
)
ON CONFLICT (version) DO NOTHING;
