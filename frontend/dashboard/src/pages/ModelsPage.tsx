import { Badge, Button, Code, Group, Stack } from "@mantine/core";
import { IconReload } from "@tabler/icons-react";
import { DataTable } from "mantine-datatable";

import type { ModelOut } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { QuickFilter } from "../components/QuickFilter";
import { useClientTable } from "../lib/clientTable";
import { useActivateModel, useModels, useRetrain } from "../hooks/admin";
import { formatTs } from "../lib/tz";

export function ModelsPage() {
  const list = useModels();
  const activate = useActivateModel();
  const retrain = useRetrain();

  const t = useClientTable<ModelOut>(list.data ?? [], {
    initialSort: { columnAccessor: "version", direction: "desc" },
    filterKeys: ["algorithm"],
  });

  return (
    <Stack>
      <PageHeader
        title="Model & retraining"
        description="Aktivasi = approval admin; efektif setelah restart API (hot-reload = masa depan)."
        actions={
          <Button leftSection={<IconReload size={16} />} onClick={() => retrain.mutate()} loading={retrain.isPending}>
            Trigger retrain
          </Button>
        }
      />
      <Group justify="flex-end">
        <QuickFilter value={t.query} onChange={t.setQuery} placeholder="Filter algoritma…" testid="models-filter" />
      </Group>
      <DataTable<ModelOut>
        data-testid="models-table"
        minHeight={180}
        withTableBorder
        borderRadius="md"
        striped
        highlightOnHover
        records={t.paged}
        idAccessor="id"
        fetching={list.isLoading}
        noRecordsText="Belum ada model"
        page={t.page}
        onPageChange={t.setPage}
        totalRecords={t.total}
        recordsPerPage={t.pageSize}
        sortStatus={t.sort}
        onSortStatusChange={t.setSort}
        columns={[
          { accessor: "version", title: "versi", sortable: true },
          { accessor: "algorithm", title: "algoritma", sortable: true },
          {
            accessor: "trained_at",
            title: "dilatih",
            sortable: true,
            render: (m) => (m.trained_at ? formatTs(m.trained_at) : "-"),
          },
          {
            accessor: "metrics",
            render: (m) => <Code>{JSON.stringify(m.metrics ?? {})}</Code>,
          },
          {
            accessor: "active",
            title: "aktif",
            sortable: true,
            render: (m) => (m.active ? <Badge color="teal">aktif</Badge> : ""),
          },
          {
            accessor: "actions",
            title: "",
            textAlign: "right",
            render: (m) =>
              m.active ? null : (
                <Button size="xs" variant="light" onClick={() => activate.mutate(m.id)}>
                  Aktifkan
                </Button>
              ),
          },
        ]}
      />
    </Stack>
  );
}
