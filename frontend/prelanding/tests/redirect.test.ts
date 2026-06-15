import { describe, expect, it } from "vitest";

import { isSafeRedirectUrl } from "../src/main";

describe("isSafeRedirectUrl (#9 defense-in-depth redirect)", () => {
  it("mengizinkan URL absolut https", () => {
    expect(isSafeRedirectUrl("https://telco.example/x?token=1")).toBe(true);
  });

  it("menolak skema berbahaya", () => {
    expect(isSafeRedirectUrl("javascript:alert(1)")).toBe(false);
    expect(isSafeRedirectUrl("data:text/html,<script>1</script>")).toBe(false);
    expect(isSafeRedirectUrl("http://telco.example/x")).toBe(false); // non-https ditolak
  });

  it("menolak nilai non-URL / kosong", () => {
    expect(isSafeRedirectUrl("/relatif")).toBe(false);
    expect(isSafeRedirectUrl("")).toBe(false);
    expect(isSafeRedirectUrl(null)).toBe(false);
    expect(isSafeRedirectUrl(undefined)).toBe(false);
  });
});
