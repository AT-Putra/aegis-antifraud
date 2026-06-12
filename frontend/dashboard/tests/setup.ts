import "@testing-library/jest-dom/vitest";

import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";

import { server } from "./server";

// Base absolut (Node fetch tak menerima URL relatif).
window.AEGIS_CONFIG = { apiBase: "http://localhost" };

// Polyfill yang dibutuhkan Mantine/Recharts di jsdom.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserverStub;
Element.prototype.scrollIntoView = () => {};

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
});
afterAll(() => server.close());
beforeEach(() => localStorage.clear());
