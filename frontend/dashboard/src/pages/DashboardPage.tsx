import { BarChart, LineChart } from "@mantine/charts";
import { Badge, Card, Group, Stack, Table, Text, ThemeIcon } from "@mantine/core";
import { IconBroadcast, IconChartBar, IconChartHistogram, IconList } from "@tabler/icons-react";
import { useState } from "react";

import type { AnalyticsFilters } from "../api/types";
import { DecisionBadge } from "../components/DecisionBadge";
import { FilterBar } from "../components/FilterBar";
import { KPICards } from "../components/KPICards";
import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingRows } from "../components/StateViews";
import { useBreakdown, useSummary, useTimeseries } from "../hooks/queries";
import { useStream } from "../hooks/useStream";
import { browserTz, formatTs } from "../lib/tz";

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
  const ts = useTimeseries("total", "day", filters);
  const bd = useBreakdown("decision", filters);
  const stream = useStream(true);

  const tsData = (ts.data ?? []).map((p) => ({
    bucket: formatTs(p.bucket_ts, filters.tz),
    value: p.value,
  }));
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
        <PanelTitle icon={IconChartHistogram} title="Total per hari" />
        {ts.isLoading ? (
          <LoadingRows rows={1} height={220} />
        ) : tsData.length === 0 ? (
          <EmptyState label="Belum ada data" hint="Tidak ada keputusan pada rentang/ filter ini." icon={IconChartHistogram} />
        ) : (
          <LineChart
            h={220}
            data={tsData}
            dataKey="bucket"
            series={[{ name: "value", label: "total", color: "indigo" }]}
            curveType="monotone"
            withDots={false}
          />
        )}
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
          <Table data-testid="live-feed" striped highlightOnHover stickyHeader>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>trx</Table.Th>
                <Table.Th>decision</Table.Th>
                <Table.Th>campaign</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {stream.feed.map((r, i) => (
                <Table.Tr key={`${r.trx_id}-${i}`}>
                  <Table.Td>
                    <Text size="sm" ff="monospace">
                      {String(r.trx_id ?? "")}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <DecisionBadge decision={r.decision != null ? String(r.decision) : null} />
                  </Table.Td>
                  <Table.Td>{String(r.campaign ?? "")}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
          {stream.feed.length === 0 ? (
            <EmptyState
              label="Menunggu keputusan masuk…"
              hint={stream.connected ? "Terhubung — keputusan baru akan muncul di sini." : "Menyambung kembali…"}
              icon={IconBroadcast}
            />
          ) : null}
        </Card>
      </Group>
    </Stack>
  );
}
