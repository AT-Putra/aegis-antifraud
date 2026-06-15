import { describe, expect, it } from "vitest";

import { compareValues } from "../src/lib/clientTable";

describe("compareValues (sort tabel admin — #8 null numeric)", () => {
  it("membandingkan angka secara numerik, bukan leksikal", () => {
    // Leksikal akan menaruh "10" < "9"; numerik harus 9 < 10.
    expect(compareValues(9, 10).cmp).toBeLessThan(0);
    expect(compareValues(10, 9).cmp).toBeGreaterThan(0);
    expect(compareValues(5, 5).cmp).toBe(0);
  });

  it("tidak menyamakan 0 dengan null (bug coercion lama)", () => {
    // Lama: null→"" lalu 0 < "" coercion → 0 dianggap setara null.
    const { cmp, bothNull } = compareValues(0, null);
    expect(bothNull).toBe(false);
    expect(cmp).toBeLessThan(0); // 0 (ada nilai) sebelum null
  });

  it("null/undefined selalu setelah nilai apa pun", () => {
    expect(compareValues(null, 100).cmp).toBeGreaterThan(0);
    expect(compareValues(100, null).cmp).toBeLessThan(0);
    expect(compareValues(undefined, "a").cmp).toBeGreaterThan(0);
  });

  it("dua null dianggap setara (ditandai bothNull)", () => {
    expect(compareValues(null, undefined)).toEqual({ cmp: 0, bothNull: true });
  });

  it("string dibanding leksikal", () => {
    expect(compareValues("apple", "banana").cmp).toBeLessThan(0);
    expect(compareValues("b", "a").cmp).toBeGreaterThan(0);
  });
});
