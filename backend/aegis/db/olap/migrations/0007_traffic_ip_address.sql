-- T-23 (audit): simpan raw IP address pengunjung di traffic_events utk audit detail
-- keputusan (card IP intelligence + JSON mentah). Idempoten (IF NOT EXISTS); baris lama →
-- default kosong. CATATAN PDP: ini menyimpan PII (IP) di OLAP (TTL 2 thn) — reversal sadar
-- atas minimisasi sebelumnya, atas keputusan pemilik (lihat ADR-018, 09 §4.3).
ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS ip_address String DEFAULT '';
