// SSE via fetch+ReadableStream (bisa kirim Bearer; EventSource tak bisa). K3/D-SSE.
import { useEffect, useRef, useState } from "react";

import { apiBase, } from "../config";
import { tokenStore } from "../api/client";

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
  kpi: Record<string, unknown> | null;
  feed: Array<Record<string, unknown>>;
  connected: boolean;
}

export function useStream(enabled = true): StreamState {
  const [state, setState] = useState<StreamState>({ kpi: null, feed: [], connected: false });
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (!enabled) return;
    const ac = new AbortController();
    (async () => {
      try {
        const token = tokenStore.get();
        const resp = await fetch(`${apiBase()}/v1/stream`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
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
    return () => ac.abort();
  }, [enabled]);

  return state;
}

function applyEvent(
  e: StreamEvent,
  setState: React.Dispatch<React.SetStateAction<StreamState>>,
  seen: Set<string>,
): void {
  if (e.event === "kpi") {
    setState((s) => ({ ...s, kpi: e.data as Record<string, unknown> }));
  } else if (e.event === "decision") {
    const row = e.data as Record<string, unknown>;
    const id = String(row.trx_id ?? Math.random());
    if (seen.has(id)) return;
    seen.add(id);
    setState((s) => ({ ...s, feed: [row, ...s.feed].slice(0, 30) }));
  }
}
