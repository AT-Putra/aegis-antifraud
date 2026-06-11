# Aegis — Panduan Integrasi Callback Billing

> Dokumen untuk **tim Billing/Telco**. Menjelaskan cara mengirim callback ke sistem Aegis (Anti Fraud) saat terjadi langganan sukses dan saat ada komplain. Skema ditentukan oleh Aegis; mohon mengikuti format di bawah. Sumber kebenaran teknis internal: `docs/private/03-interface-contracts.md §4`.

| Meta | Isi |
|------|-----|
| Versi | 0.1 |
| Status | Draft |
| Kontak | (isi PIC Aegis) |

---

## 1. Ringkas

Billing mengirim **callback (HTTP POST)** ke Aegis pada dua kejadian, ditautkan dengan **`trx_id`** (transaction id yang dibawa dari pre-landing/tracking iklan):

1. **Langganan SUKSES** (`event: "subscription"`) — termasuk status charging.
2. **Komplain** (`event: "complaint"`) — dikirim kemudian bila pelanggan komplain.

> **Penting:** langganan yang **GAGAL tidak perlu di-callback**. Hanya kirim callback subscription untuk langganan yang berhasil.

## 2. Endpoint

```
POST https://<host-aegis>/v1/callback/billing
Content-Type: application/json
```

## 3. Autentikasi (HMAC-SHA256)

Setiap request wajib menyertakan dua header:

| Header | Isi |
|--------|-----|
| `X-Aegis-Timestamp` | Waktu kirim, ISO 8601 UTC (mis. `2026-06-10T08:00:00Z`) |
| `X-Aegis-Signature` | `HMAC_SHA256(secret, X-Aegis-Timestamp + raw_body)` dalam hex |

- `secret` = shared secret yang diberikan Aegis (jangan dibagikan).
- `raw_body` = body JSON mentah persis seperti dikirim (byte-for-byte).
- **Anti-replay:** Aegis menolak request bila `X-Aegis-Timestamp` lebih dari **15 menit** dari waktu server.

**Contoh perhitungan (pseudocode):**
```
ts   = "2026-06-10T08:00:00Z"
body = '{"event":"subscription","trx_id":"abc123",...}'
sig  = hex( hmac_sha256(secret, ts + body) )
# kirim header X-Aegis-Timestamp: ts , X-Aegis-Signature: sig
```

## 4. Payload

### 4.1 Langganan sukses
```json
{
  "event": "subscription",
  "trx_id": "abc123",
  "charging_status": "success",
  "charging_fail_reason": null,
  "service_id": "SVC-001",
  "msisdn_hash": "<msisdn yang sudah di-hash oleh telco>",
  "event_time": "2026-06-10T08:00:00Z"
}
```

| Field | Wajib | Keterangan |
|-------|-------|-----------|
| `event` | ya | Selalu `"subscription"` |
| `trx_id` | ya | String ≤128 char, charset `[A-Za-z0-9._:-]` |
| `charging_status` | ya | `"success"` atau `"failed"` |
| `charging_fail_reason` | bila `failed` | `"insufficient_balance"` (pulsa kurang) atau `"daily_limit_reached"` (limit charging harian tercapai); `null` bila sukses |
| `service_id` | ya | ID layanan SMS premium yang dilanggan |
| `msisdn_hash` | ya | MSISDN yang **sudah di-hash** oleh telco (Aegis tidak menerima nomor plaintext) |
| `event_time` | ya | ISO 8601 UTC |

> Catatan: status charging bersifat **final** pada callback ini (tidak ada retry susulan).

### 4.2 Komplain
```json
{
  "event": "complaint",
  "trx_id": "abc123",
  "event_time": "2026-06-10T09:00:00Z"
}
```

| Field | Wajib | Keterangan |
|-------|-------|-----------|
| `event` | ya | Selalu `"complaint"` |
| `trx_id` | ya | `trx_id` yang sama dengan saat langganan |
| `event_time` | ya | ISO 8601 UTC |

## 5. Respons & penanganan

| HTTP | Arti | Tindakan billing |
|------|------|------------------|
| `200 {"status":"ok"}` | Diterima | Selesai |
| `401` | Signature/timestamp invalid | Cek secret & perhitungan HMAC, cek jam server (NTP) |
| `400/422` | Payload/skema salah | Perbaiki payload |
| `5xx` | Error sementara Aegis | **Retry** dengan backoff |

- **Idempoten:** mengirim callback yang sama `(event, trx_id)` lebih dari sekali aman — Aegis tidak menggandakan data. Disarankan retry bila tidak menerima `200`.
- `trx_id` yang tidak dikenal Aegis tetap diterima (`200`) dan dicatat untuk audit.

## 6. Checklist integrasi
- [ ] Dapatkan `host` Aegis & `shared secret`.
- [ ] Implementasi HMAC-SHA256 header.
- [ ] Pastikan jam server tersinkron (NTP) — penting untuk window 15 menit.
- [ ] Kirim callback subscription **hanya** untuk langganan sukses.
- [ ] Kirim callback complaint saat ada komplain (pakai `trx_id` yang sama).
- [ ] Terapkan retry untuk respons non-200.
- [ ] Uji dengan endpoint sandbox Aegis (bila tersedia).
