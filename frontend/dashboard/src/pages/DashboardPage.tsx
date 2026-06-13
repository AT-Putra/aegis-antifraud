import { BarChart } from "@mantine/charts";
import { Badge, Card, Group, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconBroadcast, IconChartBar, IconChartHistogram, IconList } from "@tabler/icons-react";
import { DataTable, type DataTableSortStatus } from "mantine-datatable";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

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
import { browserTz, formatTs } from "../lib/tz";

const FEED_PAGE_SIZE = 10;

interface ScoreBreakdown {
  rules: number | null;
  isolation_forest: number | null;
  lightgbm: number | null;
}

interface FeedRow {
  trx_id: string;
  decision: string | null;
  campaign: string | null;
  reason: string | null;
  final_score: number | null;
  score_breakdown: ScoreBreakdown;
  ts: string | null;
}

type FeedSortKey = "trx_id" | "decision" | "final_score" | "campaign" | "ts";

// Warna badge skor terhadap ambang (semantik proyek: tinggi = lebih berisiko). Selaras SearchPage.
function scoreColor(v: number | null): string {
  if (v == null) return "gray";
  if (v >= 0.7) return "red";
  if (v >= 0.4) return "yellow";
  return "teal";
}

function num(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function str(v: unknown): string | null {
  return v != null && v !== "" ? String(v) : null;
}

/** Petakan baris feed mentah (SSE, longgar) → FeedRow bertipe. */
function toFeedRow(r: Record<string, unknown>): FeedRow {
  const b = (r.score_breakdown ?? {}) as Record<string, unknown>;
  return {
    trx_id: String(r.trx_id ?? ""),
    decision: str(r.decision),
    campaign: str(r.campaign),
    reason: str(r.reason),
    final_score: num(r.final_score),
    score_breakdown: {
      rules: num(b.rules),
      isolation_forest: num(b.isolation_forest),
      lightgbm: num(b.lightgbm),
    },
    ts: str(r.ts),
  };
}

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

/** Satu sel breakdown: 3 komponen skor berlabel (R / IF / LGBM). null → "—". */
function BreakdownCell({ b }: { b: ScoreBreakdown }) {
  const parts: Array<[string, number | null]> = [
    ["R", b.rules],
    ["IF", b.isolation_forest],
    ["LGBM", b.lightgbm],
  ];
  if (parts.every(([, v]) => v == null)) return <Text c="dimmed" size="sm">—</Text>;
  return (
    <Group gap={6} wrap="nowrap">
      {parts.map(([label, v]) => (
        <Text key={label} size="xs" ff="monospace" c={v == null ? "dimmed" : undefined}>
          <Text span c="dimmed" size="xs">{label}</Text> {v == null ? "—" : v.toFixed(2)}
        </Text>
      ))}
    </Group>
  );
}

export function DashboardPage() {
  const [filters, setFilters] = useState<AnalyticsFilters>({ tz: browserTz() });
  const summary = useSummary(filters);
  const bd = useBreakdown("decision", filters);
  const stream = useStream(true);
  const navigate = useNavigate();

  const [feedPage, setFeedPage] = useState(1);
  const [feedSort, setFeedSort] = useState<DataTableSortStatus<FeedRow>>({
    columnAccessor: "ts",
    direction: "desc",
  });

  const bdData = (bd.data ?? []).map((b) => ({ key: b.key, count: b.count }));

  // Feed: 50 terbaru (buffer useStream), sort + paginate sisi-klien. Default ts desc (terbaru dulu).
  const feedRows = useMemo(() => stream.feed.map(toFeedRow), [stream.feed]);
  const feedSorted = useMemo(() => {
    const key = feedSort.columnAccessor as FeedSortKey;
    const rows = [...feedRows];
    rows.sort((a, b) => {
      const av = a[key] ?? "";
      const bv = b[key] ?? "";
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return feedSort.direction === "desc" ? -cmp : cmp;
    });
    return rows;
  }, [feedRows, feedSort]);
  const feedPaged = feedSorted.slice((feedPage - 1) * FEED_PAGE_SIZE, feedPage * FEED_PAGE_SIZE);

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
        <Text size="xs" c="dimmed" mb="sm">
          50 keputusan terbaru — urutkan kolom & klik trx untuk detail.
        </Text>
        <DataTable<FeedRow>
          data-testid="live-feed"
          minHeight={180}
          withTableBorder
          borderRadius="md"
          striped
          highlightOnHover
          records={feedPaged}
          idAccessor="trx_id"
          noRecordsText={
            stream.connected ? "Menunggu keputusan masuk…" : "Menyambung kembali…"
          }
          page={feedPage}
          onPageChange={setFeedPage}
          totalRecords={feedSorted.length}
          recordsPerPage={FEED_PAGE_SIZE}
          sortStatus={feedSort}
          onSortStatusChange={setFeedSort}
          columns={[
            {
              accessor: "trx_id",
              title: "trx",
              sortable: true,
              render: (r) => (
                <Text
                  size="sm"
                  ff="monospace"
                  c="indigo"
                  style={{ cursor: "pointer" }}
                  onClick={() => navigate(`/decision/${encodeURIComponent(r.trx_id)}`)}
                >
                  {r.trx_id}
                </Text>
              ),
            },
            {
              accessor: "decision",
              sortable: true,
              render: (r) => <DecisionBadge decision={r.decision} />,
            },
            {
              accessor: "final_score",
              title: "skor",
              sortable: true,
              textAlign: "right",
              render: (r) =>
                r.final_score == null ? (
                  <Text c="dimmed">—</Text>
                ) : (
                  <Badge color={scoreColor(r.final_score)} variant="light" radius="sm">
                    {r.final_score.toFixed(3)}
                  </Badge>
                ),
            },
            {
              accessor: "score_breakdown",
              title: "breakdown",
              render: (r) => <BreakdownCell b={r.score_breakdown} />,
            },
            {
              accessor: "campaign",
              sortable: true,
              render: (r) => r.campaign ?? <Text c="dimmed" size="sm">—</Text>,
            },
            {
              accessor: "reason",
              title: "alasan",
              render: (r) =>
                r.reason ? (
                  <Text size="sm" c="dimmed" title={r.reason}>
                    {r.reason}
                  </Text>
                ) : (
                  <Text c="dimmed" size="sm">—</Text>
                ),
            },
            {
              accessor: "ts",
              title: "waktu",
              sortable: true,
              render: (r) => (r.ts ? formatTs(r.ts) : "—"),
            },
          ]}
        />
      </Card>

      <BlockReasonsPanel filters={filters} />
      <BehaviorStatsPanel filters={filters} />
    </Stack>
  );
}
