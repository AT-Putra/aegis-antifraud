# Aegis Anti Fraud

Sistem deteksi & pencegahan fraud pada langganan SMS Premium jalur **WEB-OPT-IN**: memastikan hanya **manusia asli** yang diteruskan berlangganan, lewat scoring **device fingerprinting + user behavior** (rules + Isolation Forest + LightGBM).

Dokumentasi lengkap (sumber kebenaran) ada di `docs/private/` — mulai dari `00-README-sistem-dokumentasi.md`.

## Arsitektur singkat
- **Pre-landing page** — kumpulkan sinyal (tidak memutuskan), bawa `trx_id`/`service`/`source`/`pub_id`.
- **Scoring API (FastAPI)** — validasi → device_id → rules+AI → threshold → (jika manusia) ambil URL web-opt-in dari sistem CP (server-to-server, HMAC) → redirect; (jika robot) blokir.
- **PostgreSQL** (OLTP) · **ClickHouse** (OLAP) · **Redis** (cache/rate-limit/state) · **Caddy** (reverse proxy + TLS).

## Prasyarat
- Docker Engine 29.x + Docker Compose v2.40.x

## Mulai cepat (development)
```bash
cp .env.example .env      # lalu isi nilai rahasia
make up                   # nyalakan semua service (profil memori dev hemat)
make ps                   # cek semua healthy
curl http://localhost/health
make test                 # jalankan test
make lint                 # lint
make down                 # matikan
```

## Profil memori (parametrik)
`mem_limit` tiap service diatur via `.env`. Default = **profil dev** (≈8 GB host). Untuk produksi (host ≥12 GB) pakai nilai penuh TRD §7 yang tercantum (dikomentari) di `.env.example`. ClickHouse otomatis menskalakan diri ke 70% mem_limit-nya.

## Struktur (ringkas)
```
backend/        FastAPI scoring + ML (Python 3.13)
frontend/       pre-landing (vanilla) + dashboard (React) — menyusul
infra/          caddy, postgres, clickhouse
docs/           dokumentasi (docs/private = sumber kebenaran)
```

## Status pengembangan
Fase implementasi mengikuti `docs/private/04-task-breakdown.md`. **T-01 (skeleton + infra): selesai.** Berikutnya T-02 (skema data & migrasi).
