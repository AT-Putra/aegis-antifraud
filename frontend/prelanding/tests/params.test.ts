import { describe, expect, it } from "vitest";

import { ParamError, parseParams } from "../src/params";

describe("parseParams (AC-PL-01/03)", () => {
  it("menerima param valid + tangkap param tak dikenal ke source_params", () => {
    const p = parseParams("?trx_id=trx.1&service=funzone&campaign=promo-a&source=facebook&pub_id=123&utm=xyz");
    expect(p.service).toBe("funzone");
    expect(p.campaign).toBe("promo-a");
    expect(p.source).toBe("facebook");
    expect(p.source_params).toEqual({ utm: "xyz" });
  });

  it("campaign wajib (F-16) → ParamError bila absen", () => {
    expect(() => parseParams("?trx_id=t1&service=funzone")).toThrow(ParamError);
  });

  it("service slug huruf besar → ParamError", () => {
    expect(() => parseParams("?trx_id=t1&service=FunZone&campaign=promo-a")).toThrow(ParamError);
  });

  it("source tak valid diabaikan (nullable), bukan error", () => {
    const p = parseParams("?trx_id=t1&service=funzone&campaign=promo-a&source=bad%20space");
    expect(p.source).toBeNull();
  });
});
