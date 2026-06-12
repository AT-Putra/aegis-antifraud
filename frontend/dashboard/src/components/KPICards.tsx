// Kartu KPI ringkasan (summary). Responsif via SimpleGrid.
import { Card, SimpleGrid, Text } from "@mantine/core";

import type { Summary } from "../api/types";

const CARDS: Array<{ key: keyof Summary; label: string }> = [
  { key: "total", label: "Total" },
  { key: "allow", label: "Allow" },
  { key: "block", label: "Block" },
  { key: "weboptin_failed", label: "Web-opt-in gagal" },
  { key: "fraud_est", label: "Estimasi fraud (lolos)" },
  { key: "complaints", label: "Komplain" },
];

export function KPICards({ summary }: { summary: Summary }) {
  return (
    <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }}>
      {CARDS.map((c) => (
        <Card key={c.key} withBorder padding="md" radius="md" data-testid={`kpi-${c.key}`}>
          <Text size="xs" c="dimmed">
            {c.label}
          </Text>
          <Text fw={700} size="xl">
            {Number(summary[c.key] ?? 0)}
          </Text>
        </Card>
      ))}
    </SimpleGrid>
  );
}
