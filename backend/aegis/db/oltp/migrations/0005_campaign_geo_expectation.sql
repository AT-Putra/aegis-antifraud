-- T-25 (ADR-020): ekspektasi geo/carrier per campaign untuk fitur soft `campaign_geo_mismatch`.
-- home_country = negara asal yang DIHARAPKAN (ISO 3166-1 alpha-2, mis. 'ID'); NULL = tanpa
-- ekspektasi (fitur 0). expect_mobile_carrier = harap IP operator seluler (mis. campaign
-- billing Telkomsel). Berbeda dari allowed_countries (geo-gate hard-block, F-17): ini hanya
-- menyuplai sinyal SOFT ke scoring (bukan blokir). Aditif & idempoten: baris lama → NULL/false
-- (= tanpa ekspektasi) → tak mengubah perilaku campaign existing.
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS home_country text;
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS expect_mobile_carrier boolean NOT NULL DEFAULT false;
