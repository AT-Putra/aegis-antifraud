// Kartu KPI ringkasan (summary). Responsif via SimpleGrid.
// Tiap kartu: ikon + aksen warna semantik + angka tegas.
import { Card, Group, SimpleGrid, Text, ThemeIcon } from "@mantine/core";
import {
  IconActivity,
  IconAlertTriangle,
  IconCircleCheck,
  IconCircleX,
  IconMessageReport,
  IconShieldHalf,
  type Icon,
} from "@tabler/icons-react";

import type { Summary } from "../api/types";

interface CardDef {
  key: keyof Summary;
  label: string;
  color: string;
  icon: Icon;
}

const CARDS: CardDef[] = [
  { key: "total", label: "Total", color: "indigo", icon: IconActivity },
  { key: "allow", label: "Allow", color: "teal", icon: IconCircleCheck },
  { key: "block", label: "Block", color: "red", icon: IconCircleX },
  { key: "weboptin_failed", label: "Web-opt-in gagal", color: "orange", icon: IconAlertTriangle },
  { key: "fraud_est", label: "Estimasi fraud (lolos)", color: "grape", icon: IconShieldHalf },
  { key: "complaints", label: "Komplain", color: "yellow", icon: IconMessageReport },
];

export function KPICards({ summary }: { summary: Summary }) {
  return (
    <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }}>
      {CARDS.map((c) => {
        const Ico = c.icon;
        return (
          <Card key={c.key} withBorder padding="md" radius="md" data-testid={`kpi-${c.key}`}>
            <Group justify="space-between" align="flex-start" wrap="nowrap">
              <Text size="xs" c="dimmed">
                {c.label}
              </Text>
              <ThemeIcon color={c.color} variant="light" size="sm" radius="md">
                <Ico size={16} stroke={1.8} />
              </ThemeIcon>
            </Group>
            <Text fw={700} size="xl" mt="xs">
              {Number(summary[c.key] ?? 0)}
            </Text>
          </Card>
        );
      })}
    </SimpleGrid>
  );
}
