// Badge keputusan berwarna semantik. Label = teks keputusan apa adanya
// (allow/block) agar tetap kontraktual dengan test & mudah dibaca.
import { Badge } from "@mantine/core";

import { decisionColor } from "../lib/decision";

export function DecisionBadge({ decision }: { decision?: string | null }) {
  const text = decision ?? "";
  if (!text) return null;
  return (
    <Badge color={decisionColor(decision)} variant="light" radius="sm">
      {text}
    </Badge>
  );
}
