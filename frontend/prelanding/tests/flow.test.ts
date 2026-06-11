import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { run } from "../src/main";
import { server } from "./server";

const BASE = "http://localhost";
const OK_INIT = http.post(`${BASE}/v1/session/init`, () =>
  HttpResponse.json({ session_token: "tok", expires_at: new Date().toISOString() }),
);

function mountDom(): void {
  document.body.innerHTML = '<main id="app"><div id="state"></div></main>';
}

function stateText(): string {
  return document.getElementById("state")?.textContent ?? "";
}

beforeEach(() => {
  mountDom();
  window.AEGIS_CONFIG = { apiBase: BASE }; // base absolut utk fetch di Node
});

describe("alur pre-landing (AC-PL-01/02/03)", () => {
  it("AC-PL-01: tautan tak valid (campaign absen) → stop tanpa request", async () => {
    const r = await run({ search: "?trx_id=t1&service=svc" });
    expect(r.state).toBe("stopped");
    expect(stateText()).toContain("tidak valid");
  });

  it("AC-PL-01: campaign_not_found → pesan + stop", async () => {
    server.use(
      http.post(`${BASE}/v1/session/init`, () =>
        HttpResponse.json({ code: "campaign_not_found", message: "x" }, { status: 404 }),
      ),
    );
    const r = await run({ search: "?trx_id=t1&service=svc&campaign=nope" });
    expect(r.state).toBe("stopped");
    expect(stateText()).toContain("terdaftar");
  });

  it("AC-PL-02/03: allow → redirect; payload bawa campaign+session_token+source_params, tanpa secret", async () => {
    let body: Record<string, unknown> = {};
    server.use(
      OK_INIT,
      http.post(`${BASE}/v1/score`, async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ decision: "allow", redirect_url: "https://telco/x?token=1" });
      }),
    );
    const navigate = vi.fn();
    const r = await run({
      search: "?trx_id=trx1&service=svc&campaign=promo&source=fb&pub_id=1&utm=xyz",
      navigate,
    });
    expect(r.state).toBe("ready");
    await r.clickCta!();
    expect(navigate).toHaveBeenCalledWith("https://telco/x?token=1");
    expect(body.campaign).toBe("promo");
    expect(body.session_token).toBe("tok");
    expect(body.source_params).toEqual({ utm: "xyz" });
    expect("secret" in body).toBe(false);
    expect(body.signals).toBeTruthy();
  });

  it("AC-PL-02: block → tampilkan notice", async () => {
    server.use(
      OK_INIT,
      http.post(`${BASE}/v1/score`, () =>
        HttpResponse.json({ decision: "block", notice: "Permintaan tidak dapat diproses." }),
      ),
    );
    const r = await run({ search: "?trx_id=trx2&service=svc&campaign=promo" });
    await r.clickCta!();
    expect(stateText()).toContain("ditolak");
  });

  it("AC-PL-02: 502 weboptin_unavailable → pesan + tombol coba lagi", async () => {
    server.use(
      OK_INIT,
      http.post(`${BASE}/v1/score`, () =>
        HttpResponse.json({ code: "weboptin_unavailable", message: "x" }, { status: 502 }),
      ),
    );
    const r = await run({ search: "?trx_id=trx3&service=svc&campaign=promo" });
    await r.clickCta!();
    expect(document.getElementById("retry")).not.toBeNull();
  });
});
