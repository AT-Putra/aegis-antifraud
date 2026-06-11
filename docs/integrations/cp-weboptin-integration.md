# Aegis — Panduan Integrasi API Web-Opt-In (untuk Tim CP)

> Dokumen untuk **tim Sistem CP**. Menjelaskan cara mengimplementasi **API yang dipanggil Aegis** untuk meminta URL web-opt-in (lengkap dengan one-time token telco). Skema ditentukan oleh Aegis; mohon mengikuti format di bawah. Sumber kebenaran teknis internal: `docs/private/03-interface-contracts.md §5`.

| Meta | Isi |
|------|-----|
| Versi | 0.1 |
| Status | Draft |
| Arah | Aegis (client) → Sistem CP (server) |
| Kontak | (isi PIC Aegis) |

---

## 1. Ringkas

Alur baru dengan Aegis sebagai pre-filter di depan:

```
traffic user → pre-landing Aegis → scoring Aegis
   → (jika user diputuskan MANUSIA) Aegis POST ke API CP ini
   → CP minta one-time token ke telco
   → CP balikkan URL web-opt-in lengkap ke Aegis
   → Aegis redirect user ke URL tersebut untuk registrasi
```

CP cukup menyediakan **satu endpoint** yang: menerima POST dari Aegis, memverifikasi signature, meminta token ke telco seperti biasa, lalu mengembalikan URL web-opt-in lengkap.

> **Penting (anti-bypass):** endpoint ini **hanya boleh** melayani request yang signature HMAC-nya valid. Inilah yang mencegah bot meminta URL billable langsung ke CP tanpa lewat scoring Aegis. Tolak request tanpa signature valid.

## 2. Endpoint

URL endpoint ditentukan oleh CP dan didaftarkan di Aegis (per-layanan). Contoh:

```
POST https://cpsystem.com/request-weboptin
Content-Type: application/json
```

## 3. Autentikasi (HMAC-SHA256, secret per-layanan)

Setiap request menyertakan tiga header. CP memverifikasinya sebelum memproses:

| Header | Isi |
|--------|-----|
| `X-Aegis-Timestamp` | Waktu kirim, ISO 8601 UTC (mis. `2026-06-11T08:00:00Z`) |
| `X-Aegis-Signature` | `HMAC_SHA256(secret, X-Aegis-Timestamp + raw_body)` dalam hex |
| `X-Aegis-Request-Id` | UUID unik per request (sama dengan `request_id` di body) |

- `secret` = shared secret **per-layanan** yang disepakati Aegis–CP (beda tiap layanan/service). Jangan dibagikan.
- `raw_body` = body JSON mentah persis seperti diterima (byte-for-byte).
- **Anti-replay:** tolak bila `X-Aegis-Timestamp` lebih dari **15 menit** dari waktu server.
- **Idempotensi:** dedupe berdasarkan `X-Aegis-Request-Id` — bila request_id sudah pernah diproses, kembalikan hasil yang sama / tolak dengan aman (token telco bersifat one-time).

**Contoh verifikasi (pseudocode):**
```
expected = hex( hmac_sha256(secret, header["X-Aegis-Timestamp"] + raw_body) )
if not constant_time_equals(expected, header["X-Aegis-Signature"]): reject(401)
if abs(now - parse(header["X-Aegis-Timestamp"])) > 15 minutes:        reject(401)
if already_processed(header["X-Aegis-Request-Id"]):                   return cached_or_reject
```

## 4. Request (Aegis → CP)

```json
{
  "trx_id": "abc123",
  "service": "funzone",
  "source": "facebook",
  "pub_id": "123",
  "request_id": "e3b0c442-...-uuid",
  "requested_at": "2026-06-11T08:00:00Z"
}
```

| Field | Wajib | Keterangan |
|-------|-------|-----------|
| `trx_id` | ya | ID transaksi (≤128, charset `[A-Za-z0-9._:-]`) — pakai untuk minta token ke telco |
| `service` | ya | Slug layanan (`[a-z0-9-]`) — untuk validasi/routing di sisi CP |
| `source` | tidak | Sumber iklan (boleh `null`) |
| `pub_id` | tidak | ID publisher, dipasangkan dengan `source` (boleh `null`) |
| `request_id` | ya | UUID, sama dengan header `X-Aegis-Request-Id` |
| `requested_at` | ya | ISO 8601 UTC |

## 5. Response (CP → Aegis)

**Sukses (HTTP 200):**
```json
{ "status": "ok", "web_opt_in_url": "https://telcourl.com/transaksi/tauthwco2?token=abcasahsd" }
```
- `web_opt_in_url` = URL web-opt-in **lengkap & siap pakai** (https), sudah memuat one-time token dari telco.

**Gagal:**
```json
{ "status": "error", "reason": "token_request_failed" }
```
| HTTP | Arti | Tindakan Aegis |
|------|------|----------------|
| `200 {"status":"ok"}` | Berhasil | Redirect user ke `web_opt_in_url` |
| `200 {"status":"error"}` / `4xx` / `5xx` | Gagal mint | Tampilkan pesan ramah + tombol coba lagi (dicatat *system error*, bukan fraud) |
| timeout | Tidak menjawab dalam **5 detik** | Sama seperti gagal |

- **Timeout Aegis: 5 detik**, retry maksimal 1×. Mohon endpoint merespons cepat.

## 6. Catatan keamanan & privasi

- Aegis **tidak menyimpan token mentah** — hanya host URL + status untuk audit.
- Komunikasi **server-to-server**; browser pengguna tidak pernah memanggil endpoint ini.
- Wajib HTTPS. Tolak request non-HTTPS / tanpa signature valid.

## 7. Checklist integrasi (CP)
- [ ] Sediakan endpoint POST + daftarkan URL-nya ke Aegis (per-layanan).
- [ ] Sepakati & simpan `secret` per-layanan dengan aman.
- [ ] Verifikasi HMAC `X-Aegis-Signature` (constant-time) + window 15 menit.
- [ ] Dedupe `X-Aegis-Request-Id` (idempoten).
- [ ] Pastikan jam server tersinkron (NTP).
- [ ] Minta one-time token ke telco lalu kembalikan `web_opt_in_url` lengkap.
- [ ] Respons dalam <5 detik; kembalikan `{status:"error", reason}` bila gagal.
- [ ] Uji dengan request sandbox dari Aegis (bila tersedia).
