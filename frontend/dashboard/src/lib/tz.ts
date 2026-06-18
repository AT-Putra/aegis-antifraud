// Utilitas timezone presentasi (data tetap UTC di backend).
// Konversi wall-time↔UTC pakai offset dari Intl (WIB tanpa DST → eksak; zona ber-DST
// punya edge di jam transisi — lihat ADR-017).

const FALLBACK_TZ = "Asia/Jakarta";

// Apakah string ISO sudah membawa penanda timezone ('Z' atau ±HH:MM di akhir)?
function hasTzDesignator(iso: string): boolean {
  return /[zZ]$|[+-]\d{2}:?\d{2}$/.test(iso.trim());
}

// Timestamp OLAP sering naif (tanpa 'Z') namun bermakna UTC → tandai sbg UTC agar
// `new Date()` tak menafsirkannya sebagai waktu lokal browser.
function asUtcDate(iso: string): Date {
  const s = iso.trim().replace(" ", "T");
  return new Date(hasTzDesignator(s) ? s : `${s}Z`);
}

// Format timestamp (UTC, naif/ber-Z) → timezone pengguna untuk presentasi.
export function formatTs(iso: string, tz = FALLBACK_TZ): string {
  try {
    return new Intl.DateTimeFormat("id-ID", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: tz || FALLBACK_TZ,
    }).format(asUtcDate(iso));
  } catch {
    return iso;
  }
}

// Offset (menit) zona `tz` pada instant `date` tertentu. asUTC - date = offset.
function tzOffsetMinutes(date: Date, tz: string): number {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: tz, hourCycle: "h23",
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  }).formatToParts(date);
  const m: Record<string, string> = {};
  for (const p of parts) m[p.type] = p.value;
  const asUTC = Date.UTC(+m.year, +m.month - 1, +m.day, +m.hour, +m.minute, +m.second);
  return (asUTC - date.getTime()) / 60000;
}

// Wall-time naif ("YYYY-MM-DDTHH:mm:ss", dimaknai di `tz`) → instant UTC (ISO ber-Z).
export function wallToUtcIso(wall: string, tz: string): string {
  const s = wall.trim().replace(" ", "T");
  const provisional = new Date(`${s}Z`); // anggap UTC dulu
  if (Number.isNaN(provisional.getTime())) return wall;
  const offset = tzOffsetMinutes(provisional, tz || FALLBACK_TZ);
  return new Date(provisional.getTime() - offset * 60000).toISOString();
}

// Awal hari ini (00:00 di `tz`) sebagai wall-time naif "YYYY-MM-DDT00:00:00".
export function startOfTodayWall(tz: string): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz || FALLBACK_TZ, year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const m: Record<string, string> = {};
  for (const p of parts) m[p.type] = p.value;
  return `${m.year}-${m.month}-${m.day}T00:00:00`;
}

// Awal hari ini sebagai instant UTC (ISO ber-Z) — dipakai sbg default rentang query.
export function startOfTodayUtcIso(tz: string): string {
  return wallToUtcIso(startOfTodayWall(tz), tz);
}

// Format label bucket chart. `bucket_ts` sudah wall-time di tz (dari toTimeZone server),
// jadi diformat APA ADANYA tanpa konversi tz lagi (hindari geser ganda).
export function formatBucket(iso: string, granularity: "hour" | "day"): string {
  const d = asUtcDate(iso); // treat naif sbg UTC → komponen = wall-time tz
  if (Number.isNaN(d.getTime())) return iso;
  const opts: Intl.DateTimeFormatOptions =
    granularity === "hour"
      ? { timeZone: "UTC", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }
      : { timeZone: "UTC", day: "2-digit", month: "short" };
  try {
    return new Intl.DateTimeFormat("id-ID", opts).format(d);
  } catch {
    return iso;
  }
}

export function browserTz(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || FALLBACK_TZ;
  } catch {
    return FALLBACK_TZ;
  }
}
