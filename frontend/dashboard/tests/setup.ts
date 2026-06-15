import "@testing-library/jest-dom/vitest";

import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";

import { server } from "./server";

// localStorage polyfill. jsdom di vitest (Node 26) tak memasang window.localStorage —
// Node 26 punya global `localStorage` eksperimental yang `undefined` tanpa flag
// --localstorage-file, dan jsdom tak menimpanya. Akibatnya referensi `localStorage`
// telanjang (di app src/api/client.ts & test) resolve ke undefined. Pasang implementasi
// in-memory mandiri di window & globalThis agar perilaku == browser.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length(): number {
    return this.store.size;
  }
  clear(): void {
    this.store.clear();
  }
  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null;
  }
  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
  removeItem(key: string): void {
    this.store.delete(key);
  }
  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }
}
const memStorage = new MemoryStorage();
for (const target of [globalThis, window] as const) {
  Object.defineProperty(target, "localStorage", { configurable: true, value: memStorage });
}

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

// ADR-015: bersihkan cookie (mis. aegis_csrf dari loginAs) agar tak bocor antar-test.
function clearCookies(): void {
  for (const c of document.cookie.split(";")) {
    const name = c.split("=")[0].trim();
    if (name) document.cookie = `${name}=;expires=${new Date(0).toUTCString()};path=/`;
  }
}

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  localStorage.clear();
  clearCookies();
});
afterAll(() => server.close());
beforeEach(() => {
  localStorage.clear();
  clearCookies();
});
