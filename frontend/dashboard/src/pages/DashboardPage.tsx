import { BarChart } from "@mantine/charts";
import { Badge, Card, Group, Stack, Table, Text, ThemeIcon } from "@mantine/core";
import { IconBroadcast, IconChartBar, IconChartHistogram, IconList } from "@tabler/icons-react";
import { useState } from "react";

import type { AnalyticsFilters } from "../api/types";
import { DecisionBadge } from "../components/DecisionBadge";
import { FilterBar } from "../components/FilterBar";
import { KPICards } from "../components/KPICards";
import { MetricsChart } from "../components/MetricsChart";
import { PageHeader } from "../components/PageHeader";
import { BehaviorStatsPanel, BlockReasonsPanel } from "../components/StatsPanels";
import { EmptyState, ErrorState, LoadingRows } from "../components/StateViews";
import { useBreakdown, useSummary } from "../hooks/queries";
import { useStream } from "../hooks/useStream";
import { browserTz } from "../lib/tz";

function PanelTitle({ icon: Ico, title }: { icon: typeof IconChartBar; title: string }) {
  return (
    <Group gap="xs" mb="sm">
      <ThemeIcon variant="light" color="indigo" size="sm" radius="md">
        <Ico size={15} stroke={1.8} />
      </ThemeIcon>
      <Text fw={600}>{title}</Text>
    </Group>
  );
}

export function DashboardPage() {
  const [filters, setFilters] = useState<AnalyticsFilters>({ tz: browserTz() });
  const summary = useSummary(filters);
  const bd = useBreakdown("decision", filters);
  const stream = useStream(true);

  const bdData = (bd.data ?? []).map((b) => ({ key: b.key, count: b.count }));

  return (
    <Stack>
      <PageHeader
        title="Analitik"
        description="Ringkasan lalu lintas scoring, tren keputusan, dan aktivitas terkini."
        actions={
          <Badge
            color={stream.connected ? "teal" : "gray"}
            variant="light"
            size="lg"
            leftSection={<IconBroadcast size={13} />}
            data-testid="sse-status"
          >
            {stream.connected ? "realtime" : "terputus"}
          </Badge>
        }
      />

      <FilterBar value={filters} onChange={setFilters} />

      {summary.isLoading ? (
        <LoadingRows rows={2} height={88} />
      ) : summary.isError ? (
        <ErrorState label="Gagal memuat ringkasan." onRetry={() => summary.refetch()} />
      ) : summary.data ? (
        <KPICards summary={summary.data} />
      ) : null}

      <Card padding="md">
        <PanelTitle icon={IconChartHistogram} title="Tren per hari" />
        <Text size="xs" c="dimmed" mb="sm">
          Pilih metrik via chip untuk membandingkan data dalam satu grafik.
        </Text>
        <MetricsChart filters={filters} />
      </Card>

      <Group align="stretch" grow wrap="wrap">
        <Card padding="md">
          <PanelTitle icon={IconChartBar} title="Breakdown keputusan" />
          {bd.isLoading ? (
            <LoadingRows rows={1} height={220} />
          ) : bdData.length === 0 ? (
            <EmptyState label="Belum ada keputusan" icon={IconChartBar} />
          ) : (
            <BarChart
              h={220}
              data={bdData}
              dataKey="key"
              series={[{ name: "count", label: "jumlah", color: "indigo" }]}
            />
          )}
        </Card>

        <Card padding="md">
          <PanelTitle icon={IconList} title="Feed realtime" />
          <Table.ScrollContainer minWidth={420}>
            <Table data-testid="live-feed" striped highlightOnHover stickyHeader>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>trx</Table.Th>
                  <Table.Th>decision</Table.Th>
                  <Table.Th>campaign</Table.Th>
                  <Table.Th>alasan</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {stream.feed.map((r, i) => {
                  const reason = r.reason != null ? String(r.reason) : "";
                  return (
                    <Table.Tr key={`${r.trx_id}-${i}`}>
                      <Table.Td>
                        <Text size="sm" ff="monospace">
                          {String(r.trx_id ?? "")}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <DecisionBadge decision={r.decision != null ? String(r.decision) : null} />
                      </Table.Td>
                      <Table.Td>
                        {r.campaign ? String(r.campaign) : <Text c="dimmed" size="sm">—</Text>}
                      </Table.Td>
                      <Table.Td>
                        {reason ? (
                          <Text size="sm" c="dimmed" title={reason}>
                            {reason}
                          </Text>
                        ) : (
                          <Text c="dimmed" size="sm">—</Text>
                        )}
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
          {stream.feed.length === 0 ? (
            <EmptyState
              label="Menunggu keputusan masuk…"
              hint={stream.connected ? "Terhubung — keputusan baru akan muncul di sini." : "Menyambung kembali…"}
              icon={IconBroadcast}
            />
          ) : null}
        </Card>
      </Group>

      <BlockReasonsPanel filters={filters} />
      <BehaviorStatsPanel filters={filters} />
    </Stack>
  );
}
