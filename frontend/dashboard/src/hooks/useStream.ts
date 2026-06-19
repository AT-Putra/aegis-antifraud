// SSE via fetch+ReadableStream (kirim cookie auth via credentials; EventSource tak fleksibel).
// ADR-015: auth = cookie httpOnly (otomatis terkirim), bukan Bearer. K3/D-SSE.
// ADR-022: stream murni feed (event kpi dihapus) + filter-aware (scope service/campaign/...).
import { useEffect, useRef, useState } from "react";

import type { AnalyticsFilters } from "../api/types";
import { apiBase } from "../config";

export interface StreamEvent {
  event: string;
  data: unknown;
}

/** Parse buffer text/event-stream → daftar event (event:, data:). */
export function parseSSE(buffer: string): { events: StreamEvent[]; rest: string } {
  const events: StreamEvent[] = [];
  const blocks = buffer.split("\n\n");
  const rest = blocks.pop() ?? "";
  for (const block of blocks) {
    let ev = "message";
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) ev = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    if (dataLines.length) {
      try {
        events.push({ event: ev, data: JSON.parse(dataLines.join("\n")) });
      } catch {
        /* abaikan event tak valid */
      }
    }
  }
  return { events, rest };
}

export interface StreamState {
  feed: Array<Record<string, unknown>>;
  connected: boolean;
}

const EMPTY: StreamState = { feed: [], connected: false };

/** Scope filter (non-waktu) → query string stabil utk URL /stream + dependency reconnect. */
function scopeQuery(f?: AnalyticsFilters): string {
  const p = new URLSearchParams();
  if (f?.service) p.set("service", f.service);
  if (f?.campaign) p.set("campaign", f.campaign);
  if (f?.source) p.set("source", f.source);
  if (f?.pub_id) p.set("pub_id", f.pub_id);
  return p.toString();
}

/**
 * Feed SSE realtime. `enabled=false` (mis. filter waktu aktif → feed beku) menutup koneksi.
 * Filter scope menyaring feed di server; ganti scope → reconnect (didebounce ~400ms, ADR-022/D2).
 */
export function useStream(enabled: boolean, filters?: AnalyticsFilters): StreamState {
  const [state, setState] = useState<StreamState>(EMPTY);
  const seen = useRef<Set<string>>(new Set());
  const qs = scopeQuery(filters);

  useEffect(() => {
    if (!enabled) {
      seen.current = new Set();
      setState(EMPTY);
      return;
    }
    // Scope berubah = dataset berbeda → reset buffer & dedup sebelum (re)connect.
    seen.current = new Set();
    setState(EMPTY);
    const ac = new AbortController();
    const timer = setTimeout(() => {
      void (async () => {
        try {
          const url = `${apiBase()}/v1/stream${qs ? `?${qs}` : ""}`;
          const resp = await fetch(url, {
            credentials: "include", // cookie auth otomatis (same-origin via Caddy)
            signal: ac.signal,
          });
          if (!resp.body) return;
          setState((s) => ({ ...s, connected: true }));
          const reader = resp.body.getReader();
          const dec = new TextDecoder();
          let buf = "";
          for (;;) {
            const { value, done } = await reader.read();
            if (done) break;
            buf += dec.decode(value, { stream: true });
            const { events, rest } = parseSSE(buf);
            buf = rest;
            for (const e of events) applyEvent(e, setState, seen.current);
          }
        } catch {
          setState((s) => ({ ...s, connected: false }));
        }
      })();
    }, 400);
    return () => {
      clearTimeout(timer);
      ac.abort();
    };
  }, [enabled, qs]);

  return state;
}

function applyEvent(
  e: StreamEvent,
  setState: React.Dispatch<React.SetStateAction<StreamState>>,
  seen: Set<string>,
): void {
  // ADR-022: hanya event "decision" (feed). Event lain (mis. "error") diabaikan di sini.
  if (e.event === "decision") {
    const row = e.data as Record<string, unknown>;
    const id = String(row.trx_id ?? Math.random());
    if (seen.has(id)) return;
    seen.add(id);
    setState((s) => ({ ...s, feed: [row, ...s.feed].slice(0, 50) }));
  }
}
