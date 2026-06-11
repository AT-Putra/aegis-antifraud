-- Inisialisasi PostgreSQL Aegis (T-01).
-- Database utama dibuat oleh image via POSTGRES_DB. File ini untuk ekstensi/
-- bootstrap ringan. Skema & migrasi tabel = T-02 (db/oltp/migrations).

-- pgcrypto: util kriptografi (mis. gen_random_uuid) bila diperlukan migrasi.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
