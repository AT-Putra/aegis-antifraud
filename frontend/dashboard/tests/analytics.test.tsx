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
    // explainability absen → tak ada tabel penjelasan (degradasi anggun).
    expect(screen.queryByTestId("explainability")).not.toBeInTheDocument();
  });

  it("explainability: tabel faktor rules + komposisi + catatan model tampil", async () => {
    loginAs("admin");
    server.use(
      http.get("http://localhost/v1/analytics/decision/trx-ex", () =>
        HttpResponse.json({
          trx_id: "trx-ex", decision: "block", final_score: 0.5, weboptin_status: "na",
          score_breakdown: { rules: 0.5, isolation_forest: null, lightgbm: null },
          signals: {}, ip_intelligence: {}, device_info: {}, outcome: { reason: null },
          explainability: {
            available: true, version: "1", feature_source: "stored_features", warnings: [],
            rules_version_used: 1,
            rules: {
              formula: "rules_risk = ...", applied_mode: "weighted_formula",
              soft_sum: 0.5, soft_score: 0.5, effective_score: 0.5,
              hard_rules_enabled: ["webdriver"], hard_rules_triggered: [],
              factors: [
                { name: "automation_score", label: "Skor automasi", value: 1, weight: 0.2, contribution: 0.2 },
                { name: "webview_risk", label: "Risiko WebView", value: 1, weight: 0.3, contribution: 0.3 },
              ],
            },
            blend: {
              final_score: 0.5, threshold: 0.5, decision: "block", reason: null,
              mode: "weighted_normalized",
              components: [
                { name: "rules", label: "Rules", score: 0.5, weight: 1, normalized_weight: 1, contribution: 0.5, applied: true },
              ],
            },
            models: { attribution_available: false, note: "Atribusi per-fitur (SHAP) belum tersedia." },
            rationale: "Skor akhir 0.500 ≥ ambang 0.5 → diblokir.",
          },
        }),
      ),
    );
    renderApp(["/decision/trx-ex"]);
    const panel = await screen.findByTestId("explainability");
    expect(within(panel).getByText("Skor automasi")).toBeInTheDocument();
    expect(within(panel).getByText("Komposisi skor akhir")).toBeInTheDocument();
    expect(within(panel).getByText(/SHAP/)).toBeInTheDocument();
  });

  it("explainability: alert hard-rule + peringatan feature_source terdegradasi", async () => {
    loginAs("admin");
    server.use(
      http.get("http://localhost/v1/analytics/decision/trx-hr", () =>
        HttpResponse.json({
          trx_id: "trx-hr", decision: "block", final_score: 1, weboptin_status: "na",
          score_breakdown: { rules: 0.2, isolation_forest: null, lightgbm: null },
          signals: {}, ip_intelligence: {}, device_info: {}, outcome: { reason: "rule:webdriver" },
          explainability: {
            available: true, version: "1", feature_source: "recomputed_from_signals",
            warnings: ["Fitur direkonstruksi dari signals; ip_is_datacenter didekati."],
            rules_version_used: 1,
            rules: {
              formula: "rules_risk = ...", applied_mode: "hard_rule",
              soft_sum: 0.2, soft_score: 0.2, effective_score: 1,
              hard_rules_enabled: ["webdriver"], hard_rules_triggered: ["webdriver"],
              factors: [
                { name: "automation_score", label: "Skor automasi", value: 1, weight: 0.2, contribution: 0.2 },
              ],
            },
            blend: {
              final_score: 1, threshold: 0.5, decision: "block", reason: "rule:webdriver",
              mode: "hard_rule_forced",
              components: [
                { name: "rules", label: "Rules", score: 0.2, weight: 1, normalized_weight: 0, contribution: 0, applied: false },
              ],
            },
            models: { attribution_available: false, note: "SHAP belum tersedia." },
            rationale: "Diblokir oleh hard-rule (webdriver).",
          },
        }),
      ),
    );
    renderApp(["/decision/trx-hr"]);
    expect(await screen.findByTestId("hard-rule-alert")).toBeInTheDocument();
    expect(screen.getByTestId("feature-source-warning")).toBeInTheDocument();
  });
});
