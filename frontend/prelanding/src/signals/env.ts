// Sinyal lingkungan: automation_hints, integrity, attribution (03 §3.3). Best-effort.

type Dict = Record<string, unknown>;

const AUTOMATION_GLOBALS = [
  "webdriver", "__webdriver_evaluate", "__selenium_evaluate", "__driver_evaluate",
  "_phantom", "callPhantom", "__nightmare", "domAutomation", "cdc_adoQpoasnfa76pfcZLmcfl_Array",
];

export function collectAutomation(isTrustedCta: boolean | null): Dict {
  const w = window as unknown as Record<string, unknown>;
  const globals = AUTOMATION_GLOBALS.filter((k) => k in w);
  const nav = navigator as Navigator & { webdriver?: boolean };
  const headless = /HeadlessChrome/.test(nav.userAgent || "") || nav.webdriver === true;
  return {
    webdriver: nav.webdriver === true,
    headless_hints: headless,
    isTrusted_cta: isTrustedCta,
    automation_globals: globals,
    viewport_anomaly: (window.outerWidth || 0) === 0 || (window.outerHeight || 0) === 0,
  };
}

export function collectIntegrity(): Dict {
  let iframe = false;
  try {
    iframe = window.top !== window.self;
  } catch {
    iframe = true; // akses lintas-origin diblok → kemungkinan di-embed
  }
  return {
    ever_visible: document.visibilityState === "visible",
    visibility_state: document.visibilityState,
    iframe_embedded: iframe,
    time_skew_ms: 0,
    touch_device_consistent:
      (navigator.maxTouchPoints > 0) === ("ontouchstart" in window),
  };
}

export function collectAttribution(): Dict {
  let referrer: string | null = null;
  try {
    referrer = document.referrer ? new URL(document.referrer).host : null;
  } catch {
    referrer = null;
  }
  const lang = (navigator.language || "").toLowerCase();
  const tz = safe(() => Intl.DateTimeFormat().resolvedOptions().timeZone) || "";
  const localeConsistent = !lang || !tz ? null : tz.startsWith("Asia") ? lang.length > 0 : true;
  return { referrer, locale_consistent: localeConsistent };
}

function safe<T>(fn: () => T): T | null {
  try {
    return fn();
  } catch {
    return null;
  }
}
