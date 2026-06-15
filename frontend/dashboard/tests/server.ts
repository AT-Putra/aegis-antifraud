import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

const B = "http://localhost";

// Handler default (bisa di-override per-test via server.use()).
export const handlers = [
  // ADR-015: default = belum login (401). loginAs() meng-override agar mengembalikan role.
  http.get(`${B}/v1/users/me`, () =>
    HttpResponse.json({ code: "unauthorized", message: "no session" }, { status: 401 }),
  ),
  http.get(`${B}/v1/analytics/summary`, () =>
    HttpResponse.json({
      total: 0, allow: 0, block: 0, weboptin_failed: 0, fraud_est: 0, complaints: 0,
      charging_fail_breakdown: {},
    }),
  ),
  http.get(`${B}/v1/analytics/timeseries`, () => HttpResponse.json([])),
  http.get(`${B}/v1/analytics/breakdown`, () => HttpResponse.json([])),
  http.get(`${B}/v1/analytics/search`, () => HttpResponse.json([])),
  http.get(`${B}/v1/analytics/block-reasons`, () => HttpResponse.json([])),
  http.get(`${B}/v1/analytics/behavior-stats`, () => HttpResponse.json([])),
  http.get(`${B}/v1/registry/services`, () => HttpResponse.json([])),
  http.get(`${B}/v1/registry/campaigns`, () => HttpResponse.json([])),
  http.get(`${B}/v1/stream`, () =>
    new HttpResponse(
      'event: kpi\ndata: {"total":1}\n\nevent: decision\ndata: {"trx_id":"sse-1","decision":"block","campaign":"c","reason":"rule:webdriver"}\n\n',
      { headers: { "Content-Type": "text/event-stream" } },
    ),
  ),
];

export const server = setupServer(...handlers);
