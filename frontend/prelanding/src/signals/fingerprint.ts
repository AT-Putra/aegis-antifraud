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

// Audio fingerprint via OfflineAudioContext (ADR-025). Render DSP OFFLINE — bukan akses
// mikrofon → TANPA prompt izin. Render bersifat async (~ms); di-prime saat load lalu
// dibaca sinkron di collectFingerprint (siap jauh sebelum CTA). null bila API absen/gagal.
let _audioHash: string | null = null;

export function primeAudioFingerprint(): void {
  try {
    const Ctx =
      (window as unknown as { OfflineAudioContext?: typeof OfflineAudioContext }).OfflineAudioContext ||
      (window as unknown as { webkitOfflineAudioContext?: typeof OfflineAudioContext }).webkitOfflineAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx(1, 44100, 44100);
    const osc = ctx.createOscillator();
    osc.type = "triangle";
    osc.frequency.value = 10000;
    const comp = ctx.createDynamicsCompressor();
    comp.threshold.value = -50;
    comp.knee.value = 40;
    comp.ratio.value = 12;
    comp.attack.value = 0;
    comp.release.value = 0.25;
    osc.connect(comp);
    comp.connect(ctx.destination);
    osc.start(0);
    const onDone = (buf: AudioBuffer) => {
      const ch = buf.getChannelData(0);
      let acc = 0;
      for (let i = 4500; i < 5000; i++) acc += Math.abs(ch[i]);
      _audioHash = djb2(acc.toString());
    };
    const p = ctx.startRendering() as unknown as Promise<AudioBuffer> | undefined;
    if (p && typeof p.then === "function") p.then(onDone).catch(() => {});
    else ctx.oncomplete = (e) => onDone(e.renderedBuffer);
  } catch {
    /* degrade → null */
  }
}

// Deteksi font via pengukuran lebar teks canvas (ADR-025) — TANPA prompt izin. Font hadir
// bila lebar render berbeda dari font dasar fallback. Sinkron & best-effort.
const _FONT_PROBES = [
  "Arial", "Verdana", "Tahoma", "Times New Roman", "Courier New", "Georgia",
  "Trebuchet MS", "Roboto", "Droid Sans", "Noto Sans", "Segoe UI", "Helvetica Neue",
];
const _FONT_BASES = ["monospace", "sans-serif", "serif"];
const _FONT_TEXT = "mmmmmmmmmmlli";

function detectFonts(): string[] {
  try {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (!ctx) return [];
    const size = "72px";
    const baseW: Record<string, number> = {};
    for (const b of _FONT_BASES) {
      ctx.font = `${size} ${b}`;
      baseW[b] = ctx.measureText(_FONT_TEXT).width;
    }
    const found: string[] = [];
    for (const f of _FONT_PROBES) {
      for (const b of _FONT_BASES) {
        ctx.font = `${size} '${f}',${b}`;
        if (ctx.measureText(_FONT_TEXT).width !== baseW[b]) {
          found.push(f);
          break;
        }
      }
    }
    return found;
  } catch {
    return [];
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
    audio_hash: _audioHash, // OfflineAudioContext (di-prime saat load, prompt-free) — ADR-025
    fonts: detectFonts(), // pengukuran lebar teks canvas (prompt-free) — ADR-025
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
