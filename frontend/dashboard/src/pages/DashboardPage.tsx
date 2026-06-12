import { BarChart, LineChart } from "@mantine/charts";
import { Alert, Card, Group, Loader, Stack, Table, Text, Title } from "@mantine/core";
import { useState } from "react";

import type { AnalyticsFilters } from "../api/types";
import { FilterBar } from "../components/FilterBar";
import { KPICards } from "../components/KPICards";
import { useBreakdown, useSummary, useTimeseries } from "../hooks/queries";
import { useStream } from "../hooks/useStream";
import { browserTz, formatTs } from "../lib/tz";

export function DashboardPage() {
  const [filters, setFilters] = useState<AnalyticsFilters>({ tz: browserTz() });
  const summary = useSummary(filters);
  const ts = useTimeseries("total", "day", filters);
  const bd = useBreakdown("decision", filters);
  const stream = useStream(true);

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={3}>Analitik</Title>
        <Text size="sm" c={stream.connected ? "teal" : "dimmed"} data-testid="sse-status">
          {stream.connected ? "realtime ●" : "realtime ○"}
        </Text>
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
        <LineChart
          h={220}
          data={(ts.data ?? []).map((p) => ({ bucket: formatTs(p.bucket_ts, filters.tz), value: p.value }))}
          dataKey="bucket"
          series={[{ name: "value", label: "total" }]}
          curveType="monotone"
        />
      </Card>

      <Group align="flex-start" grow wrap="wrap">
        <Card withBorder padding="md" radius="md">
          <Text fw={600} mb="sm">
            Breakdown keputusan
          </Text>
          <BarChart
            h={220}
            data={(bd.data ?? []).map((b) => ({ key: b.key, count: b.count }))}
            dataKey="key"
            series={[{ name: "count", label: "jumlah" }]}
          />
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
                  <Table.Td>{String(r.trx_id ?? "")}</Table.Td>
                  <Table.Td>{String(r.decision ?? "")}</Table.Td>
                  <Table.Td>{String(r.campaign ?? "")}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      </Group>
    </Stack>
  );
}
