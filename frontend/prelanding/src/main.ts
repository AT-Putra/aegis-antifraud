// Orkestrasi pre-landing (T-10): param → init → kumpul sinyal → CTA → score → keputusan.
// `run()` dapat diuji (suntik search & navigate). Tanpa secret di klien (anti-bypass = token).
import { type ApiError, score, sessionInit } from "./api";
import { type Params, ParamError, parseParams } from "./params";
import { BehaviorTracker, collectSignals } from "./signals";
import * as ui from "./ui";

const INIT_ERRORS: Record<string, string> = {
  service_not_found: "Layanan tidak tersedia.",
  campaign_not_found: "Halaman tidak terdaftar.",
  forbidden_origin: "Halaman ini tidak diizinkan memproses permintaan.",
  rate_limited: "Terlalu banyak permintaan. Coba beberapa saat lagi.",
};

export interface RunResult {
  state: "stopped" | "ready";
  clickCta?: () => Promise<void>;
}

export async function run(opts: {
  search?: string;
  navigate?: (url: string) => void;
} = {}): Promise<RunResult> {
  const search = opts.search ?? (typeof location !== "undefined" ? location.search : "");
  const navigate = opts.navigate ?? ((url: string) => { window.location.href = url; });

  ui.renderLoading();

  let params: Params;
  try {
    params = parseParams(search);
  } catch (e) {
    const msg = e instanceof ParamError ? "Tautan tidak valid." : "Terjadi kesalahan.";
    ui.renderStopped(msg);
    return { state: "stopped" };
  }

  const tracker = new BehaviorTracker();
  tracker.start_tracking();

  let token: string;
  try {
    token = (await sessionInit(params)).session_token;
  } catch (e) {
    tracker.stop();
    ui.renderStopped(initMessage(e as ApiError));
    return { state: "stopped" };
  }

  const readyAt = nowMs();
  let lastSignals: ReturnType<typeof collectSignals> | null = null;

  const cta = async (isTrusted: boolean): Promise<void> => {
    ui.renderProcessing();
    lastSignals = collectSignals(tracker, { timeToCta: nowMs() - readyAt, isTrustedCta: isTrusted });
    await submit(params, token, lastSignals, navigate, () =>
      // Retry (mis. 502/expired): sesi sekali-pakai sudah dipakai → init ulang, kirim ulang.
      retry(params, lastSignals!, navigate),
    );
  };

  ui.renderReady((isTrusted) => void cta(isTrusted));
  return { state: "ready", clickCta: () => cta(true) };
}

async function submit(
  params: Params,
  token: string,
  signals: ReturnType<typeof collectSignals>,
  navigate: (url: string) => void,
  onRetry: () => void,
): Promise<void> {
  try {
    const res = await score(params, token, signals);
    if (res.decision === "allow") {
      // Defense-in-depth: backend sudah menjamin web-opt-in URL https (CP client tolak
      // non-https). Tetap verifikasi di klien agar tak pernah navigate ke skema berbahaya
      // (javascript:/data:/dll) bila kontrak backend berubah.
      if (!isSafeRedirectUrl(res.redirect_url)) {
        ui.renderStopped("Terjadi kesalahan.");
        return;
      }
      ui.renderRedirecting();
      navigate(res.redirect_url);
    } else {
      ui.renderBlock(res.notice);
    }
  } catch (e) {
    const err = e as ApiError;
    if (err.code === "weboptin_unavailable" || err.status === 401 || err.status === 0) {
      ui.renderError("Tidak dapat menyelesaikan permintaan.", onRetry);
    } else {
      ui.renderStopped(initMessage(err));
    }
  }
}

async function retry(
  params: Params,
  signals: ReturnType<typeof collectSignals>,
  navigate: (url: string) => void,
): Promise<void> {
  ui.renderProcessing();
  let token: string;
  try {
    token = (await sessionInit(params)).session_token;
  } catch (e) {
    ui.renderStopped(initMessage(e as ApiError));
    return;
  }
  await submit(params, token, signals, navigate, () => retry(params, signals, navigate));
}

function initMessage(e: ApiError): string {
  return INIT_ERRORS[e.code] ?? "Layanan sedang tidak tersedia. Coba lagi nanti.";
}

/** Hanya izinkan redirect ke URL absolut https (mirror kontrak backend; tolak javascript:/data:/dll). */
export function isSafeRedirectUrl(url: unknown): boolean {
  if (typeof url !== "string") return false;
  try {
    return new URL(url).protocol === "https:";
  } catch {
    return false; // bukan URL absolut valid → tolak
  }
}

function nowMs(): number {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

// Auto-jalankan di browser (bukan saat diimpor oleh test).
if (typeof document !== "undefined" && import.meta.env?.MODE !== "test") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => void run());
  } else {
    void run();
  }
}
