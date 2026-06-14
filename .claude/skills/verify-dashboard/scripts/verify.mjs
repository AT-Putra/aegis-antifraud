// Verifikasi tampilan tabel admin dashboard di browser nyata (chromium headless).
//
// KENAPA ADA: `mantine-datatable` TIDAK merender baris di jsdom (ScrollArea butuh
// layout nyata), jadi test Vitest hanya menguji alur modal + panggilan API — render
// baris/sort/paging/quick-filter HARUS diverifikasi di browser. Driver ini meng-intercept
// /v1/* dengan data mock multi-baris (membuktikan baris ter-render) lalu screenshot
// tiap halaman + menguji filter/sort/paging.
//
// Jalankan dari frontend/dashboard/: `node ../../.claude/skills/verify-dashboard/scripts/verify.mjs`
// Prasyarat: Vite dev server hidup di http://localhost:5173/dashboard/ (lihat SKILL.md).
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";

// Script ini hidup di .claude/skills/, tapi `playwright` ada di
// frontend/dashboard/node_modules. Resolve dari sana (jalankan dengan cwd =
// frontend/dashboard). NODE_PATH tak berlaku utk ESM import, jadi pakai require.
const require = createRequire(`${process.cwd()}/`);
const { chromium } = require("playwright");

const BASE = process.env.VERIFY_BASE || "http://localhost:5173/dashboard";
const OUT = process.env.VERIFY_OUT || "/tmp/verify-shots";
mkdirSync(OUT, { recursive: true });

// ---- data mock (jumlah baris > 1 halaman utk uji paging) ----
const services = Array.from({ length: 14 }, (_, i) => ({
  id: `s${i}`, slug: `svc-${String(i).padStart(2, "0")}`, name: `Layanan ${i}`,
  operator: i % 2 ? "Telco-A" : "Telco-B", cp_api_url: `https://cp/${i}`,
  status: i % 3 === 0 ? "inactive" : "active",
  created_at: "2026-06-12T00:00:00Z", updated_at: "2026-06-12T00:00:00Z",
}));
const campaigns = Array.from({ length: 12 }, (_, i) => ({
  id: `c${i}`, slug: `promo-${i}`, name: `Promo ${i}`, service: `svc-0${i % 3}`,
  allowed_origins: Array.from({ length: (i % 3) + 1 }, (_, j) => `https://e${j}.x`),
  status: i % 4 === 0 ? "inactive" : "active",
  created_at: "2026-06-12T00:00:00Z", updated_at: "2026-06-12T00:00:00Z",
}));
const users = Array.from({ length: 11 }, (_, i) => ({
  id: `u${i}`, username: `user${String(i).padStart(2, "0")}`,
  role: i === 0 ? "admin" : "user", active: i % 5 !== 0,
}));
const models = Array.from({ length: 7 }, (_, i) => ({
  id: `m${i}`, version: i + 1, algorithm: i % 2 ? "lightgbm" : "isolation_forest",
  trained_at: `2026-06-1${i}T03:00:00Z`, metrics: { auc: 0.9 + i / 100 }, active: i === 6,
}));
const feedback = Array.from({ length: 9 }, (_, i) => ({
  id: `f${i}`, trx_id: `trx-${i}`, decision_id: null,
  flagged_label: i % 2 ? "robot" : "human", note: `catatan ${i}`, review_status: "pending",
}));
const configVersions = Array.from({ length: 13 }, (_, i) => ({
  version: i + 1, created_by: null, created_at: `2026-06-${10 + (i % 18)}T0${i % 9}:00:00Z`,
  active: i === 12,
}));
const configActive = { version: 13, params: { vel_max: 5 }, threshold: 0.62, blend_weights: { rules: 1, lgbm: 2 }, guidelines: {} };

const routes = [
  { re: /\/v1\/admin\/services$/, body: services },
  { re: /\/v1\/admin\/campaigns$/, body: campaigns },
  { re: /\/v1\/admin\/users$/, body: users },
  { re: /\/v1\/admin\/models$/, body: models },
  { re: /\/v1\/admin\/feedback/, body: feedback },
  { re: /\/v1\/admin\/config\/versions$/, body: configVersions },
  { re: /\/v1\/admin\/config$/, body: configActive },
];

const browser = await chromium.launch({ args: ["--no-sandbox"] });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });

// inject token admin SEBELUM app load (auth = Bearer JWT di localStorage)
await ctx.addInitScript(() => {
  localStorage.setItem("aegis_jwt", "fake.jwt.token");
  localStorage.setItem("aegis_role", "admin");
});
// intercept semua /v1/* dengan data mock
await ctx.route("**/v1/**", (route) => {
  const url = route.request().url();
  if (/\/v1\/auth\/me$/.test(url)) return route.fulfill({ json: { username: "admin", role: "admin", tz: "Asia/Jakarta" } });
  const hit = routes.find((r) => r.re.test(url));
  return route.fulfill({ json: hit ? hit.body : [] });
});

const errors = [];
const page = await ctx.newPage();
page.on("console", (m) => { if (m.type() === "error") errors.push(m.text()); });
page.on("pageerror", (e) => errors.push(String(e)));

let failed = 0;
// CATATAN: data-testid ADA DI elemen <table>; baris = `table[data-testid=X] tbody tr`.
async function shot(path, testid, name) {
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
  await page.waitForSelector(`table[data-testid="${testid}"] tbody tr td`, { timeout: 10000 });
  const rows = await page.$$eval(`table[data-testid="${testid}"] tbody tr`, (trs) =>
    trs.filter((t) => t.querySelector("td")).length);
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  const ok = rows > 0;
  if (!ok) failed++;
  console.log(`${ok ? "✓" : "✗"} ${name}: rows_rendered=${rows}`);
}

await shot("/services", "services-table", "01-services");
await shot("/campaigns", "campaigns-table", "02-campaigns");
await shot("/users", "users-table", "03-users");
await shot("/models", "models-table", "04-models");
await shot("/feedback", "feedback-table", "05-feedback");
await shot("/config", "config-versions", "06-config");

// CATATAN: QuickFilter menaruh data-testid LANGSUNG di <input> (bukan wrapper).
const slugCells = () =>
  page.$$eval('table[data-testid="services-table"] tbody tr', (trs) =>
    trs.filter((t) => t.querySelector("td")).map((t) => t.querySelector("td")?.textContent));

// quick filter: ketik "svc-03" → harus tersaring jadi 1 baris
await page.goto(`${BASE}/services`, { waitUntil: "networkidle" });
await page.waitForSelector('table[data-testid="services-table"] tbody tr td');
await page.fill('[data-testid="services-filter"]', "svc-03");
await page.waitForTimeout(300);
const filtered = await slugCells();
await page.screenshot({ path: `${OUT}/07-services-filtered.png`, fullPage: true });
const filterOk = filtered.length === 1 && filtered[0] === "svc-03";
if (!filterOk) failed++;
console.log(`${filterOk ? "✓" : "✗"} filter svc-03 → rows=${JSON.stringify(filtered)}`);

// sort: klik header "slug" (default asc) → puncak berubah ke desc
await page.fill('[data-testid="services-filter"]', "");
await page.waitForTimeout(200);
const before = (await slugCells())[0];
await page.click('table[data-testid="services-table"] th:has-text("slug")');
await page.waitForTimeout(300);
const after = (await slugCells())[0];
await page.screenshot({ path: `${OUT}/08-services-sorted.png`, fullPage: true });
const sortOk = before !== after;
if (!sortOk) failed++;
console.log(`${sortOk ? "✓" : "✗"} sort slug: top ${before} → ${after}`);

// paging: ke halaman 2
await page.click('table[data-testid="services-table"] th:has-text("slug")'); // balik asc
await page.waitForTimeout(200);
await page.getByRole("button", { name: "2", exact: true }).click();
await page.waitForTimeout(300);
const page2 = await slugCells();
await page.screenshot({ path: `${OUT}/09-services-page2.png`, fullPage: true });
const pageOk = page2.length > 0 && page2[0] !== before;
if (!pageOk) failed++;
console.log(`${pageOk ? "✓" : "✗"} page2 rows=${JSON.stringify(page2)}`);

console.log(`\nconsole_errors=${errors.length}`);
if (errors.length) console.log(errors.slice(0, 5).join("\n"));
await browser.close();

console.log(`\nScreenshots → ${OUT}`);
if (failed || errors.length) {
  console.log(`HASIL: GAGAL (${failed} cek gagal, ${errors.length} console error)`);
  process.exit(1);
}
console.log("HASIL: LULUS — 6 tabel ter-render + filter/sort/paging OK, 0 console error");
