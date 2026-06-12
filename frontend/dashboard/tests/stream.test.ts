import { describe, expect, it } from "vitest";

import { parseSSE } from "../src/hooks/useStream";

describe("parseSSE (AC-DASH-02 SSE)", () => {
  it("mengurai event kpi + decision dan menyisakan blok parsial", () => {
    const buf =
      'event: kpi\ndata: {"total":5}\n\n' +
      'event: decision\ndata: {"trx_id":"t-1","decision":"block"}\n\n' +
      "event: decision\ndata: {partial";
    const { events, rest } = parseSSE(buf);
    expect(events).toHaveLength(2);
    expect(events[0]).toEqual({ event: "kpi", data: { total: 5 } });
    expect(events[1].event).toBe("decision");
    expect((events[1].data as { trx_id: string }).trx_id).toBe("t-1");
    expect(rest).toContain("partial"); // blok belum lengkap → ditahan
  });

  it("abaikan data JSON tak valid tanpa melempar", () => {
    const { events } = parseSSE("event: kpi\ndata: {bukan json}\n\n");
    expect(events).toHaveLength(0);
  });
});
