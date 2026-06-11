// Fingerprint device (03 §3.3). Best-effort: tiap probe degrade anggun (null/kosong)
// bila API browser tak tersedia (mis. di jsdom saat tes).
import { djb2 } from "./hash";

type Dict = Record<string, unknown>;

function canvasHash(): string | null {
  try {
    const c = document.createElement("canvas");
    const ctx = c.getContext("2d");
    if (!ctx) return null;
    ctx.textBaseline = "top";
    ctx.font = "14px Arial";
    ctx.fillStyle = "#069";
    ctx.fillText("Aegis☻fp", 2, 2);
    return djb2(c.toDataURL());
  } catch {
    return null;
  }
}

function webgl(): Dict {
  try {
    const c = document.createElement("canvas");
    const gl = (c.getContext("webgl") || c.getContext("experimental-webgl")) as WebGLRenderingContext | null;
    if (!gl) return {};
    const dbg = gl.getExtension("WEBGL_debug_renderer_info");
    const vendor = dbg ? String(gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL)) : null;
    const renderer = dbg ? String(gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL)) : null;
    const params = [gl.getParameter(gl.MAX_TEXTURE_SIZE), gl.getParameter(gl.MAX_RENDERBUFFER_SIZE)];
    return { vendor, renderer, params_hash: djb2(params.join("|")) };
  } catch {
    return {};
  }
}

function storageCaps(): Dict {
  const has = (fn: () => unknown) => {
    try {
      return !!fn();
    } catch {
      return false;
    }
  };
  return {
    localStorage: has(() => window.localStorage),
    sessionStorage: has(() => window.sessionStorage),
    indexedDB: has(() => window.indexedDB),
  };
}

function browserEnvironment(ua: string): Dict {
  const webview =
    /; wv\)/.test(ua) || /\bWebView\b/.test(ua) || (/(iPhone|iPad).*AppleWebKit(?!.*Safari)/.test(ua));
  let inapp: string | null = null;
  if (/FBAN|FBAV/.test(ua)) inapp = "facebook";
  else if (/Instagram/.test(ua)) inapp = "instagram";
  else if (/TikTok|musical_ly|BytedanceWebview/.test(ua)) inapp = "tiktok";
  else if (/\bLine\//.test(ua)) inapp = "line";
  const standalone =
    (window.navigator as unknown as { standalone?: boolean }).standalone === true ||
    (typeof window.matchMedia === "function" && window.matchMedia("(display-mode: standalone)").matches);
  return {
    is_webview: webview,
    webview_type: webview ? (/(iPhone|iPad)/.test(ua) ? "wkwebview" : "android_wv") : null,
    inapp_browser: inapp,
    is_standalone: !!standalone,
  };
}

export function collectFingerprint(): Dict {
  const nav = navigator;
  const ua = nav.userAgent || "";
  const s = window.screen || ({} as Screen);
  return {
    screen: {
      width: s.width ?? null,
      height: s.height ?? null,
      availWidth: s.availWidth ?? null,
      availHeight: s.availHeight ?? null,
      colorDepth: s.colorDepth ?? null,
      devicePixelRatio: window.devicePixelRatio ?? null,
    },
    webgl: webgl(),
    canvas_hash: canvasHash(),
    audio_hash: null, // OfflineAudioContext = peningkatan masa depan; null = degrade
    fonts: [], // deteksi font butuh canvas; kosong di lingkungan tanpa canvas
    timezone: safe(() => Intl.DateTimeFormat().resolvedOptions().timeZone),
    languages: Array.from(nav.languages ?? []),
    hardwareConcurrency: nav.hardwareConcurrency ?? null,
    deviceMemory: (nav as unknown as { deviceMemory?: number }).deviceMemory ?? null,
    platform: nav.platform || null,
    maxTouchPoints: nav.maxTouchPoints ?? 0,
    storage_caps: storageCaps(),
    ua_data: uaData(nav),
    browser_environment: browserEnvironment(ua),
  };
}

function uaData(nav: Navigator): Dict | null {
  const d = (nav as unknown as { userAgentData?: { brands?: unknown; mobile?: boolean; platform?: string } }).userAgentData;
  if (!d) return null;
  return { brands: d.brands ?? null, mobile: d.mobile ?? null, platform: d.platform ?? null };
}

function safe<T>(fn: () => T): T | null {
  try {
    return fn();
  } catch {
    return null;
  }
}
