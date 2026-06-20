# Aegis Anti-Fraud

Sistem deteksi & pencegahan fraud pada langganan **SMS Premium jalur WEB-OPT-IN**: memastikan hanya **manusia asli** yang diteruskan berlangganan, lewat scoring **device fingerprinting + user behavior** (rules + Isolation Forest + LightGBM).

> Status: **live di produksi** · Versi `0.3.3` · Deploy: Docker Compose di 1 VM (Caddy auto-TLS).

Dokumentasi teknis lengkap (sumber kebenaran) bersifat internal di `docs/private/` (tidak di-publish). Dokumen integrasi untuk mitra ada di [`docs/integrations/`](docs/integrations/).

---

## Arsitektur singkat

```
iklan → Pre-landing (kumpul sinyal) → Scoring API → keputusan
                                          │
              ALLOW → mint URL web-opt-in ke CP (server-to-server, HMAC) → redirect
              BLOCK → notifikasi blokir
```

- **Pre-landing page** (vanilla-TS) — mengumpulkan sinyal fingerprint + behavior; **tidak memutuskan**; membawa `trx_id`/`service`/`campaign`/`source`/`pub_id`. Portabel (dapat di-host di origin eksternal, CORS per-campaign).
- **Scoring API** (FastAPI) — validasi → `device_id` → rules + Isolation Forest + LightGBM (blend, terkalibrasi) → threshold → (jika manusia) ambil URL web-opt-in dari sistem CP via HMAC server-to-server → redirect; (jika robot) blokir. Fail-safe: model → rules-only → blokir.
- **Dashboard** (React + Mantine, SSE realtime) — analitik, pencarian, manajemen service/campaign, config rules/threshold, review feedback, retraining.

### Komponen

| Lapisan | Teknologi |
|---------|-----------|
| Scoring & ML | Python 3.13 · FastAPI · scikit-learn (Isolation Forest) · LightGBM |
| OLTP | PostgreSQL 18 |
| OLAP | ClickHouse 26.3 LTS |
| Cache / rate-limit / state | Redis 8 |
| Pre-landing | vanilla-TS + Vite |
| Dashboard | React 19 + TypeScript + Vite + Mantine 8 (SSE realtime) |
| Reverse proxy / TLS | Caddy 2.11 (HTTPS otomatis) |
| IP intelligence | MaxMind GeoLite2 + IP2Proxy LITE (self-hosted, lookup lokal) |
| Observability | Prometheus + Grafana |
| Deployment | Docker Engine + Docker Compose (1 VM) |

Keamanan: HTTPS (auto-TLS), payload anti-tamper (session token sekali-pakai), HMAC-SHA256 untuk callback billing & panggilan CP, rate-limit Redis, CORS per-campaign, auth dashboard via **cookie httpOnly + proteksi CSRF**, secret per-service terenkripsi at-rest (AES-256-GCM), container hardening, dan **fail-fast config produksi** (boot ditolak bila secret lemah). Sudah melewati security review pra-rilis.

---

## Prasyarat

- **Docker Engine 29.x** + **Docker Compose v2.40.x**
- Host: Linux (AlmaLinux 10 direkomendasikan). Dev ≈8 GB RAM; **produksi ≥12 GB RAM**.
- (Build frontend memakai container `node:24` — host tidak perlu Node terpasang.)

---

## Mulai cepat (development)

```bash
cp .env.example .env        # lalu isi nilai (dev boleh pakai default placeholder)

make prelanding             # build bundel pre-landing → frontend/prelanding/dist
make dashboard              # build bundel dashboard   → frontend/dashboard/dist

make up                     # nyalakan semua service (profil memori dev hemat)
make ps                     # cek semua healthy
make migrate                # jalankan migrasi DB (OLTP + ClickHouse) — WAJIB, tidak otomatis

curl http://localhost/health
```

Perintah lain: `make test` (test backend), `make lint`, `make logs`, `make down`, `make clean` (hapus volume — hati-hati).

> Catatan: migrasi DB **tidak** dijalankan otomatis saat startup — jalankan `make migrate` setelah service healthy. Bundel frontend di-build sebelum `make up` karena Caddy menyajikannya dari `dist/`.

---

## Deploy produksi (ringkas)

> Profil & langkah lengkap ada di runbook internal (`docs/private/10-deployment-runbook.md`). Ringkasan langkah non-sensitif:

1. **Server**: VM ≥12 GB RAM, Docker + Compose, **NTP aktif** (HMAC pakai window waktu), DNS A-record → IP VM, firewall buka **80/443 saja**.
2. **`.env` produksi**: `cp .env.example .env`, set **`APP_ENV=production`**, isi **semua secret/password dengan nilai acak kuat (≥32 byte)**, set `CADDY_DOMAIN=<domain>` + `CADDY_EMAIL=<email>` (TLS otomatis), dan profil memori produksi (lihat komentar di `.env.example`). `chmod 600 .env`.
3. **Build frontend**: `make prelanding && make dashboard`.
4. **(Opsional) IP intelligence**: taruh file DB GeoLite2/IP2Proxy di `data/geoip/` (lihat runbook); tanpa ini sistem tetap jalan dengan sinyal IP kosong (degrade anggun).
5. **Start + migrasi**: `make up` → `make ps` (healthy) → `make migrate` → `docker compose restart api`.
6. **Verifikasi**: `curl https://<domain>/health` → `{"status":"ok","env":"production"}`.
7. **Konfigurasi go-live** via dashboard (`https://<domain>/dashboard/`): ganti password admin, daftarkan service (+ `cp_api_url`/secret) & campaign (+ `allowed_origins`).
8. **Backup**: pasang cron host `0 2 * * * .../scripts/backup.sh` dan uji `make backup-test`.

> Validator startup akan **menolak boot** bila `APP_ENV=production` namun ada secret kosong/lemah/placeholder — ini disengaja.

### Integrasi mitra

- **Tim Billing/Telco** → [`docs/integrations/billing-callback-integration.md`](docs/integrations/billing-callback-integration.md)
- **Tim Sistem CP (web-opt-in)** → [`docs/integrations/cp-weboptin-integration.md`](docs/integrations/cp-weboptin-integration.md)

---

## Struktur repo (ringkas)

```
backend/        FastAPI scoring + ML + retraining (Python 3.13)
frontend/       prelanding (vanilla-TS) + dashboard (React)
infra/          caddy · postgres · clickhouse · prometheus · grafana
scripts/        backup / restore minimal
docs/           integrations (mitra) · private (internal, tidak di-publish)
docker-compose.yml · Makefile · .env.example
```

## Profil memori

`mem_limit` & `cpus` tiap service diatur via `.env` (12-factor). Default = profil dev (≈8 GB host). Untuk produksi (host ≥12 GB) pakai nilai penuh yang tercantum (dikomentari) di `.env.example`. ClickHouse otomatis menskalakan diri ke 70% dari `mem_limit`-nya.
