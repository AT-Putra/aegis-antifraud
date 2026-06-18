-- T-22 (F-17): geo-allowlist per campaign. allowed_countries = whitelist negara (ISO-3166
-- alpha-2, mis. 'ID','MY') yang BOLEH akses web-opt-in campaign. Array kosong '{}' = ALL
-- (tanpa batas). Aditif & idempoten: baris lama otomatis dapat default '{}' (= ALL) → tidak
-- mengubah perilaku campaign yang sudah ada saat migrasi di mesin produksi.
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS allowed_countries text[] NOT NULL DEFAULT '{}';
