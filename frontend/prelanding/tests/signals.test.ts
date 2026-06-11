import { describe, expect, it } from "vitest";

import { BehaviorTracker, collectSignals } from "../src/signals";

describe("collectSignals (best-effort, degrade anggun)", () => {
  it("menghasilkan kelima grup sinyal & tahan lingkungan tanpa canvas/webgl", () => {
    const t = new BehaviorTracker();
    t.start_tracking();
    const s = collectSignals(t, { timeToCta: 123, isTrustedCta: true });
    t.stop();

    for (const k of ["fingerprint", "behavior", "automation_hints", "integrity", "attribution"]) {
      expect(s[k as keyof typeof s]).toBeTruthy();
    }
    // canvas tak tersedia di jsdom → null (degrade), bukan error
    expect(s.fingerprint.canvas_hash).toBeNull();
    expect(s.automation_hints.isTrusted_cta).toBe(true);
    expect((s.behavior as { timing: { time_to_cta_ms: number } }).timing.time_to_cta_ms).toBe(123);
  });
});
