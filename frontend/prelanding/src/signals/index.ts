// Rakit objek `signals` sesuai 03 §3.3 (fingerprint+behavior wajib; sisanya kontekstual).
import { BehaviorTracker } from "./behavior";
import { collectAttribution, collectAutomation, collectIntegrity } from "./env";
import { collectFingerprint } from "./fingerprint";

export interface Signals {
  fingerprint: Record<string, unknown>;
  behavior: Record<string, unknown>;
  automation_hints: Record<string, unknown>;
  integrity: Record<string, unknown>;
  attribution: Record<string, unknown>;
}

export { BehaviorTracker };

export function collectSignals(
  tracker: BehaviorTracker,
  opts: { timeToCta: number | null; isTrustedCta: boolean | null },
): Signals {
  return {
    fingerprint: collectFingerprint(),
    behavior: tracker.summary(opts.timeToCta),
    automation_hints: collectAutomation(opts.isTrustedCta),
    integrity: collectIntegrity(),
    attribution: collectAttribution(),
  };
}
