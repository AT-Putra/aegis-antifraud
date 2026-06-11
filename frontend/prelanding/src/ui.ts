// Render state pre-landing (responsif, aksesibel). Tanpa logika bisnis.

function host(): HTMLElement {
  const el = document.getElementById("state");
  if (!el) throw new Error("#state tak ada");
  return el;
}

function set(html: string): void {
  host().innerHTML = html;
}

export function renderLoading(): void {
  set('<p class="muted">Memeriksa…</p>');
}

export function renderStopped(message: string): void {
  set(`<h1>Tidak dapat melanjutkan</h1><p class="muted">${esc(message)}</p>`);
}

export function renderReady(onCta: (isTrusted: boolean) => void): void {
  set(
    '<h1>Verifikasi</h1><p class="muted">Tekan tombol untuk melanjutkan ke layanan.</p>' +
      '<button id="cta" class="cta" type="button">Lanjutkan</button>',
  );
  const btn = document.getElementById("cta") as HTMLButtonElement | null;
  btn?.addEventListener("click", (e) => {
    btn.disabled = true;
    onCta(e.isTrusted);
  });
}

export function renderProcessing(): void {
  set('<p class="muted">Memproses…</p>');
}

export function renderBlock(notice: string): void {
  set(`<h1>Permintaan ditolak</h1><p class="muted">${esc(notice)}</p>`);
}

export function renderError(message: string, onRetry: () => void): void {
  set(
    `<h1>Sedang ada gangguan</h1><p class="muted">${esc(message)}</p>` +
      '<button id="retry" class="cta" type="button">Coba lagi</button>',
  );
  document.getElementById("retry")?.addEventListener("click", () => onRetry());
}

export function renderRedirecting(): void {
  set('<p class="muted">Mengalihkan…</p>');
}

function esc(s: string): string {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));
}
