// Chart tren multi-metrik dengan legend chip toggle untuk banding data.
// Default: keempat metrik OLAP tampil dalam 1 chart; klik chip untuk sembunyikan/
// tampilkan kembali tiap garis.
// Catatan: timeseries backend kini mendukung 4 metrik OLAP (total/allow/block/
// weboptin_failed). fraud_est & complaints (join OLTP) menyusul — lihat TRD §2.
import { LineChart } from "@mantine/charts";
import { Chip, Group } from "@mantine/core";
import { useState } from "react";

import type { AnalyticsFilters } from "../api/types";
import { useTimeseries } from "../hooks/queries";
import { formatBucket, startOfTodayUtcIso, wallToUtcIso } from "../lib/tz";
import { EmptyState, LoadingRows } from "./StateViews";
import { IconChartHistogram } from "@tabler/icons-react";

// Granularitas adaptif (ADR-017): rentang efektif ≤2 hari → per jam (intraday hari ini),
// >2 hari → per hari. Rentang efektif memakai default "hari ini" yg sama dgn query.
function granularityFor(filters: AnalyticsFilters): "hour" | "day" {
  const tz = filters.tz || "Asia/Jakarta";
  const fromMs = new Date(
    filters.from ? wallToUtcIso(filters.from, tz) : startOfTodayUtcIso(tz),
  ).getTime();
  const toMs = filters.to ? new Date(wallToUtcIso(filters.to, tz)).getTime() : Date.now();
  return (toMs - fromMs) / 86_400_000 <= 2 ? "hour" : "day";
}

// Warna selaras KPICards/decision: total=indigo, allow=teal, block=red, weboptin=orange.
const METRICS = [
  { key: "total", label: "Total", color: "indigo" },
  { key: "allow", label: "Allow", color: "teal" },
  { key: "block", label: "Block", color: "red" },
  { key: "weboptin_failed", label: "Web-opt-in gagal", color: "orange" },
] as const;

type MetricKey = (typeof METRICS)[number]["key"];

export function MetricsChart({ filters }: { filters: AnalyticsFilters }) {
  // Default semua metrik tampil.
  const [visible, setVisible] = useState<MetricKey[]>(METRICS.map((m) => m.key));

  const gran = granularityFor(filters);
  // Satu query per metrik (hook dipanggil tetap & berurutan — aman aturan hooks).
  const qTotal = useTimeseries("total", gran, filters);
  const qAllow = useTimeseries("allow", gran, filters);
  const qBlock = useTimeseries("block", gran, filters);
  const qWeboptin = useTimeseries("weboptin_failed", gran, filters);
  const queries: Record<MetricKey, typeof qTotal> = {
    total: qTotal,
    allow: qAllow,
    block: qBlock,
    weboptin_failed: qWeboptin,
  };

  const isLoading = METRICS.some((m) => queries[m.key].isLoading);

  // Gabung per bucket: { bucket, total, allow, block, weboptin_failed }.
  const byBucket = new Map<string, Record<string, number | string>>();
  for (const m of METRICS) {
    for (const p of queries[m.key].data ?? []) {
      const label = formatBucket(p.bucket_ts, gran);
      const row = byBucket.get(p.bucket_ts) ?? { bucket: label };
      row[m.key] = p.value;
      byBucket.set(p.bucket_ts, row);
    }
  }
  const data = [...byBucket.entries()]
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([, row]) => row);

  const series = METRICS.filter((m) => visible.includes(m.key)).map((m) => ({
    name: m.key,
    label: m.label,
    color: m.color,
  }));

  return (
    <>
      <Group gap="xs" mb="sm">
        <Chip.Group multiple value={visible} onChange={(v) => setVisible(v as MetricKey[])}>
          {METRICS.map((m) => (
            <Chip key={m.key} value={m.key} color={m.color} variant="light" size="sm">
              {m.label}
            </Chip>
          ))}
        </Chip.Group>
      </Group>

      {isLoading ? (
        <LoadingRows rows={1} height={240} />
      ) : data.length === 0 ? (
        <EmptyState label="Belum ada data" hint="Tidak ada keputusan pada rentang/filter ini." icon={IconChartHistogram} />
      ) : series.length === 0 ? (
        <EmptyState label="Tidak ada metrik dipilih" hint="Aktifkan minimal satu metrik dari chip di atas." icon={IconChartHistogram} />
      ) : (
        <LineChart
          h={240}
          data={data}
          dataKey="bucket"
          series={series}
          curveType="monotone"
          withDots={false}
          withLegend
        />
      )}
    </>
  );
}
