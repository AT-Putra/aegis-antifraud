import { Badge, Button, Group, Modal, Select, Stack, Textarea, TextInput } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconPlus } from "@tabler/icons-react";
import { DataTable } from "mantine-datatable";
import { useState } from "react";

import type { CampaignOut } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { QuickFilter } from "../components/QuickFilter";
import { useClientTable } from "../lib/clientTable";
import { useCampaigns, useSaveCampaign } from "../hooks/admin";

interface Draft {
  id?: string;
  slug: string;
  name: string;
  service: string;
  origins: string; // satu origin per baris
  status: "active" | "inactive";
}
const EMPTY: Draft = { slug: "", name: "", service: "", origins: "", status: "active" };

function parseOrigins(s: string): string[] {
  return s.split("\n").map((x) => x.trim()).filter(Boolean);
}

export function CampaignsPage() {
  const list = useCampaigns();
  const save = useSaveCampaign();
  const [opened, { open, close }] = useDisclosure(false);
  const [d, setD] = useState<Draft>(EMPTY);
  const editing = !!d.id;

  const t = useClientTable<CampaignOut>(list.data ?? [], {
    initialSort: { columnAccessor: "slug", direction: "asc" },
    filterKeys: ["slug", "name", "service", "status"],
  });

  const startCreate = () => {
    setD(EMPTY);
    open();
  };
  const startEdit = (c: CampaignOut) => {
    setD({ id: c.id, slug: c.slug, name: c.name, service: c.service, origins: (c.allowed_origins ?? []).join("\n"), status: c.status });
    open();
  };
  const submit = () => {
    const body: Record<string, unknown> = editing
      ? { name: d.name, allowed_origins: parseOrigins(d.origins), status: d.status }
      : { slug: d.slug, name: d.name, service: d.service, allowed_origins: parseOrigins(d.origins) };
    save.mutate({ id: d.id, body }, { onSuccess: close });
  };

  return (
    <Stack>
      <PageHeader
        title="Campaign (pre-landing portabel)"
        description="Tiap campaign = satu pre-landing dengan whitelist origin (CORS) sendiri."
        actions={
          <Button leftSection={<IconPlus size={16} />} onClick={startCreate}>
            Tambah
          </Button>
        }
      />
      <Group justify="flex-end">
        <QuickFilter value={t.query} onChange={t.setQuery} placeholder="Filter campaign…" testid="campaigns-filter" />
      </Group>
      <DataTable<CampaignOut>
        data-testid="campaigns-table"
        minHeight={180}
        withTableBorder
        borderRadius="md"
        striped
        highlightOnHover
        records={t.paged}
        idAccessor="id"
        fetching={list.isLoading}
        noRecordsText="Belum ada campaign"
        page={t.page}
        onPageChange={t.setPage}
        totalRecords={t.total}
        recordsPerPage={t.pageSize}
        sortStatus={t.sort}
        onSortStatusChange={t.setSort}
        columns={[
          { accessor: "slug", sortable: true },
          { accessor: "name", title: "nama", sortable: true },
          { accessor: "service", sortable: true },
          {
            accessor: "allowed_origins",
            title: "origins",
            render: (c) => (
              <Badge variant="light" color="gray">
                {(c.allowed_origins ?? []).length} origin
              </Badge>
            ),
          },
          {
            accessor: "status",
            sortable: true,
            render: (c) => (
              <Badge color={c.status === "active" ? "teal" : "gray"} variant="light">
                {c.status}
              </Badge>
            ),
          },
          {
            accessor: "actions",
            title: "",
            textAlign: "right",
            render: (c) => (
              <Button size="xs" variant="light" onClick={() => startEdit(c)}>
                Edit
              </Button>
            ),
          },
        ]}
      />

      <Modal opened={opened} onClose={close} title={editing ? "Edit campaign" : "Tambah campaign"}>
        <Stack>
          <TextInput label="Slug" value={d.slug} disabled={editing} onChange={(e) => setD({ ...d, slug: e.currentTarget.value })} />
          <TextInput label="Nama" value={d.name} onChange={(e) => setD({ ...d, name: e.currentTarget.value })} />
          <TextInput label="Service (slug)" value={d.service} disabled={editing} onChange={(e) => setD({ ...d, service: e.currentTarget.value })} />
          <Textarea label="Allowed origins (satu per baris)" autosize minRows={2} value={d.origins} onChange={(e) => setD({ ...d, origins: e.currentTarget.value })} />
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
