// Pemetaan warna semantik keputusan scoring. Dipusatkan agar konsisten
// di feed realtime, tabel pencarian, dan halaman detail.
export type DecisionColor = "teal" | "red" | "gray";

export function decisionColor(decision?: string | null): DecisionColor {
  if (decision === "allow") return "teal";
  if (decision === "block") return "red";
  return "gray";
}

// Status web-opt-in (minted/failed/na) → warna.
export function weboptinColor(status?: string | null): string {
  if (status === "minted") return "teal";
  if (status === "failed") return "red";
  return "gray";
}
