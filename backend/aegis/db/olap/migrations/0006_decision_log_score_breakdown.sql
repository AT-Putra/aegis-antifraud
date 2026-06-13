-- Feed realtime (F-08): rincian skor per-komponen di feed SSE. score_breakdown =
-- {rules, isolation_forest, lightgbm} (tiap nilai float|null), dihasilkan scoring engine.
-- Disimpan di decision_log (BUKAN JOIN ke traffic_events) agar feed hot-path tetap baca
-- 1 tabel. Idempoten. Data lama (sebelum migrasi) score_breakdown kosong → breakdown null.

ALTER TABLE decision_log ADD COLUMN IF NOT EXISTS score_breakdown String;
