-- Feed realtime (F-08): tampilkan alasan keputusan. reason dihasilkan scoring engine
-- (mis. "rule:webdriver", "failsafe:model_error_rules_only", NULL saat lolos normal).
-- Idempoten. Data lama (sebelum migrasi) reason kosong.

ALTER TABLE decision_log ADD COLUMN IF NOT EXISTS reason String;
