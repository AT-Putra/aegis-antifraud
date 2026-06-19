// T-28 — Redam console.warn recharts 3 "width(-1) height(-1) of chart should be
// greater than 0" yang muncul sekali per mount chart (Analitik/Dashboard).
//
// AKAR MASALAH (regresi recharts 3, BUKAN bug kita):
//   recharts `ResponsiveContainer` merender frame pertama dengan `initialDimension`
//   {-1,-1} sebelum ResizeObserver-nya mengukur ukuran asli; pada frame itu warn()
//   menyala walau chart render normal & self-correct. `@mantine/charts` (9.3.2) tak
//   meneruskan prop (`initialDimension`/`minWidth`/`aspect`) yang bisa mencegahnya,
//   jadi tak ada jalur perbaikan lewat API publik komponen. recharts `LogUtils.warn`
//   memakai `isDev = true` hardcoded → warning ikut muncul di build produksi.
//
// JEMBATAN SEMENTARA: fix hulu SUDAH ada (recharts issue #6716 / PR #7174 merged
//   2026-03-27) tetapi BELUM dirilis stabil — baru ada di `recharts@3.9.0-canary.0`.
//   recharts 3.8.1 (terpasang) rilis 2026-03-25, dua hari sebelum merge → belum memuat
//   fix. Begitu recharts >=3.9.0 STABIL rilis: upgrade recharts lalu HAPUS file ini +
//   impornya di main.tsx (cek tiap rilis Aegis — lihat 04-task-breakdown T-28).
//
// Filter ini sengaja sesempit mungkin: hanya membuang pesan dengan substring stabil
// di bawah; semua warning lain (termasuk warn recharts lain) tetap lolos apa adanya.

const RECHARTS_RESIZE_WARN = "of chart should be greater than 0";

const originalWarn = console.warn.bind(console);

console.warn = (...args: unknown[]) => {
  if (typeof args[0] === "string" && args[0].includes(RECHARTS_RESIZE_WARN)) {
    return; // recharts3 frame pengukuran -1 (T-28; cabut saat upgrade recharts >=3.9.0 stabil)
  }
  originalWarn(...args);
};
