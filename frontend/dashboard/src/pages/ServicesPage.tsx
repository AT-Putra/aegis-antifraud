import { Badge, Button, Group, Modal, Select, Stack, TextInput } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconPlus } from "@tabler/icons-react";
import { DataTable } from "mantine-datatable";
import { useState } from "react";

import type { ServiceOut } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { QuickFilter } from "../components/QuickFilter";
import { useClientTable } from "../lib/clientTable";
import { useSaveService, useServices } from "../hooks/admin";

interface Draft {
  id?: string;
  slug: string;
  name: string;
  operator: string;
  cp_api_url: string;
  hmac_secret: string;
  status: "active" | "inactive";
}
const EMPTY: Draft = { slug: "", name: "", operator: "", cp_api_url: "", hmac_secret: "", status: "active" };

export function ServicesPage() {
  const list = useServices();
  const save = useSaveService();
  const [opened, { open, close }] = useDisclosure(false);
  const [d, setD] = useState<Draft>(EMPTY);
  const editing = !!d.id;

  const t = useClientTable<ServiceOut>(list.data ?? [], {
    initialSort: { columnAccessor: "slug", direction: "asc" },
    filterKeys: ["slug", "name", "operator", "status"],
  });

  const startCreate = () => {
    setD(EMPTY);
    open();
  };
  const startEdit = (s: ServiceOut) => {
    setD({ id: s.id, slug: s.slug, name: s.name, operator: s.operator ?? "", cp_api_url: s.cp_api_url, hmac_secret: "", status: s.status });
    open();
  };
  const submit = () => {
    const body: Record<string, unknown> = editing
      ? { name: d.name, operator: d.operator || null, cp_api_url: d.cp_api_url, status: d.status }
      : { slug: d.slug, name: d.name, operator: d.operator || null, cp_api_url: d.cp_api_url };
    if (d.hmac_secret) body.hmac_secret = d.hmac_secret;
    save.mutate({ id: d.id, body }, { onSuccess: close });
  };

  return (
    <Stack>
      <PageHeader
        title="Layanan"
        description="Service registry: operator, endpoint API CP, dan secret HMAC per-layanan."
        actions={
          <Button leftSection={<IconPlus size={16} />} onClick={startCreate}>
            Tambah
          </Button>
        }
      />
      <Group justify="flex-end">
        <QuickFilter value={t.query} onChange={t.setQuery} placeholder="Filter layanan…" testid="services-filter" />
      </Group>
      <DataTable<ServiceOut>
        data-testid="services-table"
        minHeight={180}
        withTableBorder
        borderRadius="md"
        striped
        highlightOnHover
        records={t.paged}
        idAccessor="id"
        fetching={list.isLoading}
        noRecordsText="Belum ada layanan"
        page={t.page}
        onPageChange={t.setPage}
        totalRecords={t.total}
        recordsPerPage={t.pageSize}
        sortStatus={t.sort}
        onSortStatusChange={t.setSort}
        columns={[
          { accessor: "slug", sortable: true },
          { accessor: "name", title: "nama", sortable: true },
          { accessor: "operator", sortable: true },
          {
            accessor: "status",
            sortable: true,
            render: (s) => (
              <Badge color={s.status === "active" ? "teal" : "gray"} variant="light">
                {s.status}
              </Badge>
            ),
          },
          {
            accessor: "actions",
            title: "",
            textAlign: "right",
            render: (s) => (
              <Button size="xs" variant="light" onClick={() => startEdit(s)}>
                Edit
              </Button>
            ),
          },
        ]}
      />

      <Modal opened={opened} onClose={close} title={editing ? "Edit layanan" : "Tambah layanan"}>
        <Stack>
          <TextInput label="Slug" value={d.slug} disabled={editing} onChange={(e) => setD({ ...d, slug: e.currentTarget.value })} />
          <TextInput label="Nama" value={d.name} onChange={(e) => setD({ ...d, name: e.currentTarget.value })} />
          <TextInput label="Operator" value={d.operator} onChange={(e) => setD({ ...d, operator: e.currentTarget.value })} />
          <TextInput label="CP API URL (https)" value={d.cp_api_url} onChange={(e) => setD({ ...d, cp_api_url: e.currentTarget.value })} />
          <TextInput label="HMAC secret (write-only)" placeholder={editing ? "(kosongkan = tak diubah)" : ""} value={d.hmac_secret} onChange={(e) => setD({ ...d, hmac_secret: e.currentTarget.value })} />
          {editing && (
            <Select label="Status" data={["active", "inactive"]} value={d.status} onChange={(v) => setD({ ...d, status: (v as "active" | "inactive") ?? "active" })} />
          )}
          <Button onClick={submit} loading={save.isPending}>
            Simpan
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
