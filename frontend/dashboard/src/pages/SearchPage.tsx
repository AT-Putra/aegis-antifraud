import { Anchor, Button, Group, TextInput } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import { DataTable, type DataTableSortStatus } from "mantine-datatable";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { SearchResultItem } from "../api/types";
import { DecisionBadge } from "../components/DecisionBadge";
import { PageHeader } from "../components/PageHeader";
import { useSearch } from "../hooks/queries";
import { formatTs } from "../lib/tz";

const FIELDS = ["trx_id", "device_id", "decision", "service", "campaign", "source", "pub_id", "country", "browser"];
const PAGE_SIZE = 15;

type SortKey = keyof Pick<SearchResultItem, "trx_id" | "decision" | "service" | "campaign" | "final_score" | "ts">;

export function SearchPage() {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [active, setActive] = useState<Record<string, unknown> | null>(null);
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<DataTableSortStatus<SearchResultItem>>({
    columnAccessor: "ts",
    direction: "desc",
  });
  const navigate = useNavigate();
  const q = useSearch(active ?? {}, active !== null);

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.currentTarget.value; // tangkap sebelum updater async (event dinetralkan)
    setDraft((d) => ({ ...d, [k]: val }));
  };

  const run = () => {
    const params: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(draft)) if (v) params[k] = v;
    setActive(params);
    setPage(1);
  };

  // Sort + paginate sisi-klien (hasil search sudah dibatasi server).
  const sorted = useMemo(() => {
    const rows = [...(q.data ?? [])];
    const key = sort.columnAccessor as SortKey;
    rows.sort((a, b) => {
      const av = a[key] ?? "";
      const bv = b[key] ?? "";
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sort.direction === "desc" ? -cmp : cmp;
    });
    return rows;
  }, [q.data, sort]);

  const paged = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <>
      <PageHeader
        title="Pencarian"
        description="Telusuri keputusan berdasarkan trx, perangkat, layanan, campaign, atau atribut lain. Urutkan kolom & klik trx untuk detail."
      />
      <Group gap="xs" wrap="wrap" align="flex-end" my="md">
        {FIELDS.map((f) => (
          <TextInput key={f} aria-label={f} placeholder={f} value={draft[f] ?? ""} onChange={set(f)} />
        ))}
        <Button onClick={run} leftSection={<IconSearch size={16} />}>
          Cari
        </Button>
      </Group>

      <DataTable<SearchResultItem>
        data-testid="results"
        minHeight={180}
        withTableBorder
        borderRadius="md"
        striped
        highlightOnHover
        records={paged}
        idAccessor="trx_id"
        fetching={q.isFetching}
        noRecordsText={active !== null ? "Tidak ada hasil untuk filter ini." : "Masukkan filter lalu klik Cari."}
        page={page}
        onPageChange={setPage}
        totalRecords={sorted.length}
        recordsPerPage={PAGE_SIZE}
        sortStatus={sort}
        onSortStatusChange={setSort}
        columns={[
          {
            accessor: "trx_id",
            title: "trx_id",
            sortable: true,
            render: (r) => (
              <Anchor onClick={() => navigate(`/decision/${encodeURIComponent(r.trx_id)}`)}>
                {r.trx_id}
              </Anchor>
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
            render: (r) => (r.final_score == null ? "—" : r.final_score.toFixed(3)),
          },
          { accessor: "service", sortable: true },
          { accessor: "campaign", sortable: true },
          {
            accessor: "ts",
            title: "waktu",
            sortable: true,
            render: (r) => formatTs(r.ts),
          },
        ]}
      />
    </>
  );
}
