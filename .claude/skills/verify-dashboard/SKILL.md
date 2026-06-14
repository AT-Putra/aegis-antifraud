---
name: verify-dashboard
description: Verifikasi tampilan tabel admin dashboard (Config/Layanan/Campaign/Feedback/Model/Users) di browser nyata via Playwright+Chromium. Pakai saat diminta verifikasi render/sort/paging/quick-filter mantine-datatable yang TIDAK bisa diuji di jsdom (Vitest). Render baris, filter, sort, dan pagination dibuktikan dengan screenshot.
---

# Verifikasi tampilan dashboard di browser

`frontend/dashboard` adalah SPA Vite (React 19 + Mantine 8). Tabel admin pakai
**`mantine-datatable`**, yang **tidak merender baris di jsdom** (ScrollArea butuh
layout nyata) — jadi test Vitest hanya menguji alur modal + panggilan API. **Render
baris, quick-filter, sort kolom, dan pagination HARUS diverifikasi di browser nyata.**
Skill ini melakukannya: Vite dev server + Chromium headless (Playwright) yang
meng-intercept `/v1/*` dengan data mock multi-baris, lalu screenshot tiap halaman.

## Prasyarat (sekali per mesin)

Mesin ini **AlmaLinux 10** (RHEL-family, `dnf` — BUKAN Debian). `playwright
install-deps` GAGAL karena mencari `apt-get`. Pasang lib chromium via `dnf`:

```bash
dnf install -y atk at-spi2-atk at-spi2-core cups-libs libXcomposite libXdamage \
  libXrandr libXfixes libxkbcommon mesa-libgbm pango alsa-lib nss nspr
```

Playwright + browser (devDependency SENGAJA tidak di-commit — lihat catatan di bawah):

```bash
cd frontend/dashboard
npm i -D playwright@latest          # ke node_modules saja
npx playwright install chromium
```

Cek cepat apakah sudah siap: `rpm -q atk nss mesa-libgbm` dan
`ls node_modules/.bin/playwright`. Jika ada, lewati langkah di atas.

## Menjalankan

```bash
cd frontend/dashboard

# 1. dev server (background) — base /dashboard/, port 5173
(npm run dev >/tmp/vite-dev.log 2>&1 &)
timeout 40 bash -c 'until curl -sf http://localhost:5173/dashboard/ >/dev/null 2>&1; do sleep 1; done' && echo UP

# 2. driver verifikasi (intercept /v1/*, screenshot 6 halaman + interaksi)
node ../../.claude/skills/verify-dashboard/scripts/verify.mjs

# 3. stop dev server
pkill -f vite
```

Driver mencetak per halaman `✓ NN-nama: rows_rendered=N` lalu baris
filter/sort/paging, dan diakhiri `HASIL: LULUS` / `GAGAL` (exit code ikut).
Screenshot ke `/tmp/verify-shots/` (`01-services.png` … `09-services-page2.png`).
**Lihat screenshot-nya** — `rows_rendered>0` membuktikan baris ada, tapi mata
mengonfirmasi badge/tombol/layout. Read beberapa PNG kunci (filtered, sorted, page2).

## Cara kerja auth & mock (kenapa ini perlu)

- **Auth** = Bearer JWT di `localStorage` (`aegis_jwt` + `aegis_role`); `isAuthed`
  butuh keduanya. Driver inject keduanya via `addInitScript` sebelum app load —
  tak perlu backend/login nyata.
- **API base** = `apiBase()` default string kosong → app fetch ke `/v1/*` relatif
  origin dev server → Playwright `ctx.route("**/v1/**")` bisa intercept semua.
- **Data mock** sengaja >1 halaman (services 14, config 13, dll) supaya pagination
  benar-benar teruji.

## Gotcha yang sudah kena (jangan temukan ulang)

- **`data-testid` ada DI elemen `<table>`**, bukan ancestor. Selektor baris yang
  benar: `table[data-testid="services-table"] tbody tr` — BUKAN
  `[data-testid=...] table tbody tr` (itu 0 hasil).
- **`QuickFilter` menaruh `data-testid` LANGSUNG di `<input>`** (Mantine TextInput),
  jadi isi via `page.fill('[data-testid="services-filter"]', ...)` tanpa ` input`.
- **React controlled input**: pakai `page.fill`/`type`, jangan set `.value` via eval
  (tak memicu onChange).
- **First paint Vite lambat**: pakai `waitForSelector`/`networkidle`, jangan `sleep`.
- **Cleanup**: hapus artefak sementara & `pkill -f vite` sebelum selesai. JANGAN
  commit `playwright` ke `package.json` (sesi T-16 sengaja menjaga manifest bersih;
  build runtime via `node:24`, tak butuh browser). Biarkan terpasang di
  `node_modules` lokal saja.

## testid tiap tabel

`services-table`, `campaigns-table`, `users-table`, `models-table`,
`feedback-table`, `config-versions`. Filter: `<entity>-filter` (mis.
`services-filter`). Jika halaman/testid berubah, sesuaikan `routes`/`shot()` di
`scripts/verify.mjs`.
