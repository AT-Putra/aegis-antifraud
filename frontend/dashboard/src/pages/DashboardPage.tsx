import { BarChart, LineChart } from "@mantine/charts";
import { Alert, Badge, Card, Group, Loader, Stack, Table, Text } from "@mantine/core";
import { IconBroadcast } from "@tabler/icons-react";
import { useState } from "react";

import type { AnalyticsFilters } from "../api/types";
import { DecisionBadge } from "../components/DecisionBadge";
import { FilterBar } from "../components/FilterBar";
import { KPICards } from "../components/KPICards";
import { PageHeader } from "../components/PageHeader";
import { useBreakdown, useSummary, useTimeseries } from "../hooks/queries";
import { useStream } from "../hooks/useStream";
import { browserTz, formatTs } from "../lib/tz";

function Empty({ label }: { label: string }) {
  return (
    <Text size="sm" c="dimmed" ta="center" py="xl">
      {label}
    </Text>
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
      <Group justify="space-between" align="flex-start">
        <PageHeader
          title="Analitik"
          description="Ringkasan lalu lintas scoring, tren keputusan, dan aktivitas terkini."
        />
        <Badge
          color={stream.connected ? "teal" : "gray"}
          variant="light"
          leftSection={<IconBroadcast size={13} />}
          data-testid="sse-status"
        >
          {stream.connected ? "realtime" : "terputus"}
        </Badge>
      </Group>

      <FilterBar value={filters} onChange={setFilters} />

      {summary.isLoading ? (
        <Loader />
      ) : summary.isError ? (
        <Alert color="red">Gagal memuat ringkasan.</Alert>
      ) : summary.data ? (
        <KPICards summary={summary.data} />
      ) : null}

      <Card withBorder padding="md" radius="md">
        <Text fw={600} mb="sm">
          Total per hari
        </Text>
        {tsData.length === 0 ? (
          <Empty label="Belum ada data pada rentang ini." />
        ) : (
          <LineChart
            h={220}
            data={tsData}
            dataKey="bucket"
            series={[{ name: "value", label: "total" }]}
            curveType="monotone"
          />
        )}
      </Card>

      <Group align="flex-start" grow wrap="wrap">
        <Card withBorder padding="md" radius="md">
          <Text fw={600} mb="sm">
            Breakdown keputusan
          </Text>
          {bdData.length === 0 ? (
            <Empty label="Belum ada keputusan." />
          ) : (
            <BarChart
              h={220}
              data={bdData}
              dataKey="key"
              series={[{ name: "count", label: "jumlah" }]}
            />
          )}
        </Card>

        <Card withBorder padding="md" radius="md">
          <Text fw={600} mb="sm">
            Feed realtime
          </Text>
          <Table data-testid="live-feed" striped highlightOnHover>
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
            <Empty label="Menunggu keputusan masuk…" />
          ) : null}
        </Card>
      </Group>
    </Stack>
  );
}
