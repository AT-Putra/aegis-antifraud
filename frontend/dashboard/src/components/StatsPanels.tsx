// Panel statistik analitik: Top-10 alasan blok (bar) + rata-rata metrik behavior (grid).
import { BarChart } from "@mantine/charts";
import { Card, Group, SimpleGrid, Text, ThemeIcon } from "@mantine/core";
import { IconActivity, IconHandStop } from "@tabler/icons-react";

import type { AnalyticsFilters } from "../api/types";
import { useBehaviorStats, useBlockReasons } from "../hooks/queries";
import { EmptyState, ErrorState, LoadingRows } from "./StateViews";

function PanelTitle({ icon: Ico, title, hint }: { icon: typeof IconHandStop; title: string; hint?: string }) {
  return (
    <Group gap="xs" mb="sm" align="center">
      <ThemeIcon variant="light" color="indigo" size="sm" radius="md">
        <Ico size={15} stroke={1.8} />
      </ThemeIcon>
      <Text fw={600}>{title}</Text>
      {hint ? (
        <Text size="xs" c="dimmed">
          {hint}
        </Text>
      ) : null}
    </Group>
  );
}

export function BlockReasonsPanel({ filters }: { filters: AnalyticsFilters }) {
  const q = useBlockReasons(filters, 10);
  const data = (q.data ?? []).map((r) => ({ reason: r.reason, jumlah: r.count }));

  return (
    <Card padding="md">
      <PanelTitle icon={IconHandStop} title="Top 10 alasan blok" hint="terbanyak → tersedikit" />
      {q.isLoading ? (
        <LoadingRows rows={1} height={260} />
      ) : q.isError ? (
        <ErrorState label="Gagal memuat alasan blok." onRetry={() => q.refetch()} />
      ) : data.length === 0 ? (
        <EmptyState label="Belum ada keputusan blok" icon={IconHandStop} />
      ) : (
        <BarChart
          h={Math.max(220, data.length * 34)}
          data={data}
          dataKey="reason"
          orientation="vertical"
          yAxisProps={{ width: 160 }}
          series={[{ name: "jumlah", label: "jumlah", color: "red" }]}
          withTooltip
        />
      )}
    </Card>
  );
}

export function BehaviorStatsPanel({ filters }: { filters: AnalyticsFilters }) {
  const q = useBehaviorStats(filters);
  const stats = q.data ?? [];
  const sample = stats[0]?.sample ?? 0;

  return (
    <Card padding="md">
      <PanelTitle
        icon={IconActivity}
        title="Statistik behavior"
        hint={sample > 0 ? `rata-rata atas ${sample} sesi` : undefined}
      />
      {q.isLoading ? (
        <LoadingRows rows={2} height={64} />
      ) : q.isError ? (
        <ErrorState label="Gagal memuat statistik behavior." onRetry={() => q.refetch()} />
      ) : stats.length === 0 || sample === 0 ? (
        <EmptyState label="Belum ada data behavior" hint="Belum ada interaksi pre-landing tercatat pada rentang/filter ini." icon={IconActivity} />
      ) : (
        <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="md">
          {stats.map((s) => (
            <div key={s.metric}>
              <Text size="xs" c="dimmed">
                {s.label}
              </Text>
              <Text fw={700} size="lg">
                {s.avg.toLocaleString("id-ID", { maximumFractionDigits: 2 })}
              </Text>
            </div>
          ))}
        </SimpleGrid>
      )}
    </Card>
  );
}
