# Aegis Pre-landing (T-10)

Halaman pre-landing **portabel**: mengumpulkan sinyal fingerprint+behavior, memanggil
scoring Aegis, lalu redirect (allow) / blokir (block). **Tanpa secret di klien** — anti-bypass
memakai `session_token` sekali-pakai yang ditandatangani server (F-02). Lihat TRD §2, ADR-013,
kontrak `03 §3`.

## Build

```bash
# host tanpa Node — pakai container:
docker run --rm -v "$PWD":/app -w /app node:24 sh -c "npm ci && npm run build"
# hasil: dist/ (statis)
```

Set base URL API saat build (atau override runtime, lihat di bawah):

```bash
VITE_AEGIS_API_BASE=https://aegis.example.com  # domain Aegis
```

## Hosting di tempat lain (portabilitas)

1. **Daftarkan campaign** di Aegis (admin) dengan `allowed_origins` memuat origin host kamu, mis.
   `POST /v1/admin/campaigns { slug, name, service, allowed_origins: ["https://promo.mitra.com"] }`.
2. **Deploy `dist/`** ke host mana pun (origin = yang didaftarkan di langkah 1), via HTTPS.
3. **Arahkan ke API Aegis** — salah satu:
   - build dengan `VITE_AEGIS_API_BASE`, atau
   - override runtime tanpa rebuild: tambahkan di `index.html` sebelum bundel:
     ```html
     <script>window.AEGIS_CONFIG = { apiBase: "https://aegis.example.com" }</script>
     ```
4. **URL traffic** membawa param: `?trx_id=...&service=<slug>&campaign=<slug>&source=...&pub_id=...`
   (`trx_id`, `service`, `campaign` **wajib**).

Syarat: origin terdaftar di `allowed_origins` campaign (else `403 forbidden_origin`), dan
HTTPS di kedua sisi (hindari mixed-content). Tak ada rahasia yang perlu ditaruh di host.

## Tes

```bash
docker run --rm -v "$PWD":/app -w /app node:24 sh -c "npm ci && npm test"
```
