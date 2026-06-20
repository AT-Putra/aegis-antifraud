// F-11: tombol salin JSON di Detail Keputusan (signals mentah + seluruh respons).
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { server } from "./server";
import { loginAs, renderApp } from "./utils";

const DECISION = {
  trx_id: "trx-1",
  decision: "allow",
  final_score: 0.2,
  score_breakdown: { rules: 0.2, isolation_forest: null, lightgbm: null },
  signals: { fingerprint: { canvas_hash: "abc123" }, behavior: { mouse: { move_count: 3 } } },
  ip_intelligence: {},
  device_info: {},
  outcome: {},
};

describe("DecisionPage — tombol salin JSON", () => {
  beforeEach(() => {
    loginAs("user");
    server.use(
      http.get("http://localhost/v1/analytics/decision/:trxId", () => HttpResponse.json(DECISION)),
    );
  });

  it("menyalin signals mentah & seluruh respons ke clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText } });

    renderApp(["/decision/trx-1"]);
    await screen.findByText("Keputusan");

    // Buka kedua accordion lalu salin.
    fireEvent.click(screen.getByText("Signals (data mentah)"));
    fireEvent.click(await screen.findByTestId("copy-signals"));
    await waitFor(() =>
      expect(writeText).toHaveBeenCalledWith(JSON.stringify(DECISION.signals, null, 2)),
    );

    fireEvent.click(screen.getByText("Seluruh respons (JSON mentah)"));
    fireEvent.click(await screen.findByTestId("copy-raw"));
    await waitFor(() =>
      expect(writeText).toHaveBeenCalledWith(JSON.stringify(DECISION, null, 2)),
    );
  });
});
