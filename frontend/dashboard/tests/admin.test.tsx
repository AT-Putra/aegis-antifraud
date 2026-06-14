import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "./server";
import { loginAs, renderApp } from "./utils";

const B = "http://localhost";

// Catatan (preseden F-11/SearchPage): baris `mantine-datatable` TIDAK ter-render di jsdom
// (ScrollArea butuh layout nyata). Maka test AC-DASH-03 menguji yang dapat dilihat jsdom —
// alur modal create/edit via tombol header + assert panggilan API + kehadiran tabel.
// Aksi baris (Edit/Muat/Terima/Aktifkan) diverifikasi di browser.

describe("AC-DASH-03 manajemen", () => {
  it("services: tabel tampil + create (modal → POST)", async () => {
    loginAs("admin");
    let posted: Record<string, unknown> | null = null;
    server.use(
      http.get(`${B}/v1/admin/services`, () =>
        HttpResponse.json([
          { id: "s1", slug: "svc-a", name: "A", operator: "Op", cp_api_url: "https://cp/x",
            status: "active", created_at: "2026-06-12T00:00:00Z", updated_at: "2026-06-12T00:00:00Z" },
        ]),
      ),
      http.post(`${B}/v1/admin/services`, async ({ request }) => {
        posted = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ id: "s2" });
      }),
    );
    renderApp(["/services"]);
    // Tabel ter-render (isi baris diverifikasi di browser — caveat jsdom datatable).
    expect(await screen.findByTestId("services-table")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Tambah" }));
    await userEvent.type(await screen.findByLabelText("Slug"), "svc-b");
    await userEvent.type(screen.getByLabelText("Nama"), "B");
    await userEvent.type(screen.getByLabelText("CP API URL (https)"), "https://cp/y");
    await userEvent.type(screen.getByLabelText("HMAC secret (write-only)"), "rahasia");
    await userEvent.click(screen.getByRole("button", { name: "Simpan" }));
    await waitFor(() => expect(posted).toMatchObject({ slug: "svc-b", hmac_secret: "rahasia" }));
  });

  it("campaign: create dengan allowed_origins", async () => {
    loginAs("admin");
    let posted: Record<string, unknown> | null = null;
    server.use(
      http.get(`${B}/v1/admin/campaigns`, () => HttpResponse.json([])),
      http.post(`${B}/v1/admin/campaigns`, async ({ request }) => {
        posted = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ id: "c1" });
      }),
    );
    renderApp(["/campaigns"]);
    await userEvent.click(await screen.findByRole("button", { name: "Tambah" }));
    await userEvent.type(await screen.findByLabelText("Slug"), "promo");
    await userEvent.type(screen.getByLabelText("Nama"), "Promo");
    await userEvent.type(screen.getByLabelText("Service (slug)"), "svc-a");
    await userEvent.type(screen.getByLabelText("Allowed origins (satu per baris)"), "https://ext.example");
    await userEvent.click(screen.getByRole("button", { name: "Simpan" }));
    await waitFor(() =>
      expect(posted).toMatchObject({ slug: "promo", service: "svc-a", allowed_origins: ["https://ext.example"] }),
    );
  });

  it("config: editor termuat dari versi aktif → Simpan PUT", async () => {
    // Rollback (Muat dari baris riwayat) = aksi baris → diverifikasi di browser.
    // Di jsdom kita verifikasi editor termuat dari config aktif & Simpan mengirim PUT.
    loginAs("admin");
    let put: Record<string, unknown> | null = null;
    server.use(
      http.get(`${B}/v1/admin/config`, () =>
        HttpResponse.json({ version: 2, params: { a: 2 }, threshold: 0.7, blend_weights: { rules: 1 }, guidelines: {} }),
      ),
      http.get(`${B}/v1/admin/config/versions`, () =>
        HttpResponse.json([
          { version: 1, created_by: null, created_at: "2026-06-12T00:00:00Z", active: false },
          { version: 2, created_by: null, created_at: "2026-06-12T01:00:00Z", active: true },
        ]),
      ),
      http.put(`${B}/v1/admin/config`, async ({ request }) => {
        put = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({ version: 3 });
      }),
    );
    renderApp(["/config"]);
    expect(await screen.findByTestId("config-versions")).toBeInTheDocument();
    // Editor terisi dari config aktif (threshold 0.7, params {a:2}) via useEffect.
    await waitFor(() => expect(screen.getByLabelText("Params (JSON)")).toHaveValue(JSON.stringify({ a: 2 }, null, 2)));
    await userEvent.click(screen.getByRole("button", { name: /Simpan/ }));
    await waitFor(() => expect(put).toMatchObject({ threshold: 0.7, params: { a: 2 } }));
  });

  it("feedback: tabel pending termuat (GET)", async () => {
    // Aksi Terima/Tolak = aksi baris → diverifikasi di browser.
    loginAs("admin");
    let called = false;
    server.use(
      http.get(`${B}/v1/admin/feedback`, ({ request }) => {
        called = new URL(request.url).searchParams.get("status") === "pending";
        return HttpResponse.json([{ id: "f1", trx_id: "t1", decision_id: null, flagged_label: "robot", note: "x", review_status: "pending" }]);
      }),
    );
    renderApp(["/feedback"]);
    expect(await screen.findByTestId("feedback-table")).toBeInTheDocument();
    await waitFor(() => expect(called).toBe(true));
  });
});
