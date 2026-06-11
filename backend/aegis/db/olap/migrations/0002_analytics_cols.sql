-- T-14 (analytics, 03 §7): kolom dimensi device + rincian skor untuk breakdown/search/detail.
-- Idempoten (IF NOT EXISTS). Baris lama → kolom default kosong (analitik loss/degrade-tolerant).

ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS browser String;
ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS os String;
ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS device_type String;
ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS device_brand String;
ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS device_model String;
ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS is_webview UInt8;
ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS score_breakdown String;
