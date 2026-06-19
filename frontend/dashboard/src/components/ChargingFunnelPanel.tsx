// T-30: panel "in-depth" outcome langganan di Analitik. Melengkapi KPI cards (highlight):
// registrasi sukses (callback subscription) → charging sukses (rasio %), total gagal charging
// + breakdown (pulsa/limit/lainnya), dan komplain. Sumber OLAP via useChargingFunnel —
// perilaku live 60dtk / beku saat filter waktu (identik komponen agregat lain, ADR-022).
import { DonutChart } from "@mantine/charts";
import { Card, Center, Group, RingProgress, SimpleGrid, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconReceipt2 } from "@tabler/icons-react";

import type { AnalyticsFilters } from "../api/types";
import { useChargingFunnel } from "../hooks/queries";
import { EmptyState, ErrorState, LoadingRows } from "./StateViews";

// Alasan gagal kanonik (selaras OutcomeFilters/search) + warna semantik.
const FAIL_META = [
  { key: "insufficient_balance", label: "Pulsa tidak cukup", color: "orange" },
  { key: "daily_limit_reached", label: "Limit charging harian", color: "red" },
  { key: "other", label: "Kegagalan lainnya", color: "gray" },
] as const;

const idID = (n: number) => n.toLocaleString("id-ID");

function Tile({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text fw={700} size="lg" c={color}>
        {idID(value)}
      </Text>
    </div>
  );
}

export function ChargingFunnelPanel({ filters }: { filters: AnalyticsFilters }) {
  const q = useChargingFunnel(filters);
  const d = q.data;

  const ratio =
    d && d.registration_success > 0 ? (d.charging_success / d.registration_success) * 100 : 0;
  // Hijau jika mayoritas charged, kuning jika sedang, merah jika rendah.
  const ratioColor = ratio >= 70 ? "teal" : ratio >= 40 ? "yellow" : "red";

  const donutData = FAIL_META.map((m) => ({
    name: m.label,
    value: d?.charging_fail_breakdown[m.key] ?? 0,
    color: m.color,
  })).filter((s) => s.value > 0);

  return (
    <Card padding="md" data-testid="charging-funnel">
      <Group gap="xs" mb="sm" align="center">
        <ThemeIcon variant="light" color="indigo" size="sm" radius="md">
          <IconReceipt2 size={15} stroke={1.8} />
        </ThemeIcon>
        <Text fw={600}>Funnel langganan & charging</Text>
        <Text size="xs" c="dimmed">
          registrasi → charging → outcome
        </Text>
      </Group>

      {q.isLoading ? (
        <LoadingRows rows={1} height={180} />
      ) : q.isError ? (
        <ErrorState label="Gagal memuat funnel charging." onRetry={() => q.refetch()} />
      ) : !d || (d.registration_success === 0 && d.complaints === 0) ? (
        <EmptyState
          label="Belum ada data outcome"
          hint="Belum ada callback langganan/komplain pada rentang/filter ini."
          icon={IconReceipt2}
        />
      ) : (
        <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
          {/* Kiri: rasio (ring) + angka funnel */}
          <Group align="center" wrap="nowrap" gap="lg">
            <RingProgress
              size={132}
              thickness={12}
              roundCaps
              sections={[{ value: ratio, color: ratioColor }]}
              label={
                <Center>
                  <Stack gap={0} align="center">
                    <Text fw={700} size="lg">
                      {ratio.toFixed(1)}%
                    </Text>
                    <Text size="xs" c="dimmed">
                      charging
                    </Text>
                  </Stack>
                </Center>
              }
            />
            <SimpleGrid cols={2} spacing="sm" style={{ flex: 1 }}>
              <Tile label="Registrasi sukses" value={d.registration_success} />
              <Tile label="Charging sukses" value={d.charging_success} color="teal" />
              <Tile label="Gagal charging" value={d.charging_failed} color="red" />
              <Tile label="Komplain" value={d.complaints} color="yellow" />
            </SimpleGrid>
          </Group>

          {/* Kanan: breakdown gagal charging (donut + legenda) */}
          <div>
            <Text size="sm" fw={600} mb="xs">
              Breakdown gagal charging
            </Text>
            {d.charging_failed === 0 ? (
              <EmptyState label="Tidak ada kegagalan charging" icon={IconReceipt2} />
            ) : (
              <Group align="center" gap="lg" wrap="nowrap">
                <DonutChart
                  h={150}
                  data={donutData}
                  withTooltip
                  chartLabel={`${idID(d.charging_failed)} gagal`}
                  thickness={18}
                />
                <Stack gap={6}>
                  {FAIL_META.map((m) => {
                    const v = d.charging_fail_breakdown[m.key] ?? 0;
                    return (
                      <Group key={m.key} gap="xs" wrap="nowrap">
                        <ThemeIcon size={12} radius="xl" color={m.color} variant="filled">
                          <span />
                        </ThemeIcon>
                        <Text size="sm">{m.label}</Text>
                        <Text size="sm" fw={600}>
                          {idID(v)}
                        </Text>
                      </Group>
                    );
                  })}
                </Stack>
              </Group>
            )}
          </div>
        </SimpleGrid>
      )}
    </Card>
  );
}
