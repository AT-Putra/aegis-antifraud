import { describe, expect, it } from "vitest";

import {
  formatBucket,
  formatTs,
  startOfTodayUtcIso,
  startOfTodayWall,
  wallToUtcIso,
} from "../src/lib/tz";

// ADR-017: presentasi timezone & konversi wall↔UTC untuk default rentang Analitik.
describe("tz utils", () => {
  it("formatTs memperlakukan timestamp naif (tanpa Z) sebagai UTC", () => {
    // Naif & ber-Z harus identik (keduanya UTC) → feed OLAP naif tak salah-parse lokal.
    expect(formatTs("2026-06-18T05:00:00", "UTC")).toBe(formatTs("2026-06-18T05:00:00Z", "UTC"));
    // String berspasi (gaya ClickHouse) juga diperlakukan UTC.
    expect(formatTs("2026-06-18 05:00:00", "UTC")).toBe(formatTs("2026-06-18T05:00:00Z", "UTC"));
  });

  it("formatTs mengkonversi ke timezone pengguna (UTC ≠ WIB)", () => {
    const utc = formatTs("2026-06-18T00:00:00Z", "UTC");
    const wib = formatTs("2026-06-18T00:00:00Z", "Asia/Jakarta");
    expect(utc).not.toBe(wib); // +7 → tampilan berbeda
  });

  it("wallToUtcIso: wall-time WIB → instant UTC (geser -7 jam)", () => {
    expect(wallToUtcIso("2026-06-18T00:00:00", "Asia/Jakarta")).toBe("2026-06-17T17:00:00.000Z");
    // UTC → tanpa geser.
    expect(wallToUtcIso("2026-06-18T00:00:00", "UTC")).toBe("2026-06-18T00:00:00.000Z");
  });

  it("startOfTodayWall = jam 00:00 & konsisten dgn startOfTodayUtcIso", () => {
    const tz = "Asia/Jakarta";
    expect(startOfTodayWall(tz).endsWith("T00:00:00")).toBe(true);
    expect(startOfTodayUtcIso(tz)).toBe(wallToUtcIso(startOfTodayWall(tz), tz));
  });

  it("formatBucket: bucket sudah wall-time tz → tak digeser lagi", () => {
    // Jam 05:00 wall harus tampil mengandung "05" (bukan digeser ke 12).
    const label = formatBucket("2026-06-18T05:00:00", "hour");
    expect(label).toMatch(/05[.:]00/);
    expect(formatBucket("2026-06-18T00:00:00", "day")).toMatch(/18/);
  });
});
