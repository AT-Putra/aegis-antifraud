import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "./server";
import { loginAs, renderApp } from "./utils";

describe("AC-DASH-02 analitik realtime + pencarian + detail", () => {
  it("KPI summary + feed SSE tampil", async () => {
    loginAs("admin");
    server.use(
      http.get("http://localhost/v1/analytics/summary", () =>
        HttpResponse.json({
          total: 42, allow: 30, block: 12, weboptin_failed: 1, fraud_est: 3, complaints: 2,
          charging_fail_breakdown: {},
        }),
      ),
    );
    renderApp(["/"]);
    await waitFor(() =>
      expect(within(screen.getByTestId("kpi-total")).getByText("42")).toBeInTheDocument(),
    );
    // Panel feed realtime ter-render (isi via SSE; parsing diuji di stream.test.ts).
    expect(screen.getByTestId("live-feed")).toBeInTheDocument();
  });

  // F-11 dipecah: (1) pencarian memanggil API & form bekerja; (2) detail keputusan
  // tampil di route /decision/:trx. Baris tabel mantine-datatable TIDAK ter-render di
  // jsdom (ScrollArea butuh layout nyata) — diverifikasi di browser; lihat preseden SSE.
  it("pencarian: form memanggil API search (F-11 bagian 1)", async () => {
    loginAs("admin");
    let called = "";
    server.use(
      http.get("http://localhost/v1/analytics/search", ({ request }) => {
        called = new URL(request.url).searchParams.get("trx_id") ?? "";
        return HttpResponse.json([
          {
            trx_id: "trx-9", device_id: "d1", service: "svc", campaign: "promo",
            source: "fb", pub_id: "1", decision: "allow", weboptin_status: "minted",
            final_score: 0.2, ts: "2026-06-12T03:00:00Z",
          },
        ]);
      }),
    );
    renderApp(["/search"]);
    await userEvent.type(await screen.findByLabelText("trx_id"), "trx-9");
    await userEvent.click(screen.getByRole("button", { name: "Cari" }));
    await waitFor(() => expect(called).toBe("trx-9"));
  });

  it("detail keputusan tampil dari route /decision/:trx (F-11 bagian 2)", async () => {
    loginAs("admin");
    server.use(
      http.get("http://localhost/v1/analytics/decision/trx-9", () =>
        HttpResponse.json({
          trx_id: "trx-9", device_id: "d1", service: "svc", campaign: "promo", source: "fb",
          pub_id: "1", decision: "allow", weboptin_status: "minted", weboptin_host: "telco",
          final_score: 0.2, score_breakdown: { rules: 0.1 }, signals: {}, ip_intelligence: {},
          device_info: {}, rules_version: 1, model_version: 0, outcome: {},
        }),
      ),
    );
    renderApp(["/decision/trx-9"]);
    await waitFor(() => expect(screen.getByTestId("decision-meta")).toBeInTheDocument());
    expect(within(screen.getByTestId("decision-meta")).getByText("allow")).toBeInTheDocument();
  });
});
