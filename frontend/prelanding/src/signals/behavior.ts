// Pelacak perilaku (03 §3.3): mouse/scroll/touch + timing. Ringkasan agregat (bukan raw).

type Dict = Record<string, unknown>;

export class BehaviorTracker {
  private start = now();
  private moves = 0;
  private dirChanges = 0;
  private lastX: number | null = null;
  private lastDir: number | null = null;
  private velocities: number[] = [];
  private lastT: number | null = null;
  private taps = 0;
  private maxScrollPct = 0;
  private interactions = 0;
  private detach: Array<() => void> = [];

  start_tracking(): void {
    this.on(window, "mousemove", (e) => this.onMove(e as MouseEvent));
    this.on(window, "scroll", () => this.onScroll(), true);
    this.on(window, "touchstart", () => { this.taps++; this.interactions++; });
    this.on(window, "click", () => this.interactions++);
    this.on(window, "keydown", () => this.interactions++);
  }

  stop(): void {
    this.detach.forEach((fn) => fn());
    this.detach = [];
  }

  /** Ringkasan untuk dikirim sebagai `signals.behavior`. */
  summary(timeToCta: number | null): Dict {
    const mean =
      this.velocities.length > 0
        ? this.velocities.reduce((a, b) => a + b, 0) / this.velocities.length
        : 0;
    return {
      mouse: { move_count: this.moves, velocity_mean: round(mean), direction_changes: this.dirChanges },
      scroll: { depth_pct: Math.round(this.maxScrollPct) },
      touch: { tap_count: this.taps },
      timing: {
        interaction_count: this.interactions,
        dwell_ms: Math.round(now() - this.start),
        time_to_cta_ms: timeToCta == null ? null : Math.round(timeToCta),
      },
    };
  }

  private onMove(e: MouseEvent): void {
    this.moves++;
    const t = now();
    if (this.lastX != null && this.lastT != null) {
      const dx = e.clientX - this.lastX;
      const dt = Math.max(1, t - this.lastT);
      this.velocities.push(Math.abs(dx) / dt);
      const dir = Math.sign(dx);
      if (dir !== 0 && this.lastDir != null && dir !== this.lastDir) this.dirChanges++;
      if (dir !== 0) this.lastDir = dir;
    }
    this.lastX = e.clientX;
    this.lastT = t;
  }

  private onScroll(): void {
    const doc = document.documentElement;
    const max = (doc.scrollHeight || 0) - (window.innerHeight || 0);
    if (max > 0) this.maxScrollPct = Math.max(this.maxScrollPct, (window.scrollY / max) * 100);
  }

  private on(t: EventTarget, ev: string, fn: (e: Event) => void, passive = false): void {
    t.addEventListener(ev, fn, { passive } as AddEventListenerOptions);
    this.detach.push(() => t.removeEventListener(ev, fn));
  }
}

function now(): number {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}
function round(n: number): number {
  return Math.round(n * 1000) / 1000;
}
