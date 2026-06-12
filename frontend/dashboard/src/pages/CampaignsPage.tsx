import { Button, Group, Modal, Select, Stack, Table, Textarea, TextInput, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useState } from "react";

import type { CampaignOut } from "../api/types";
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
      <Group justify="space-between">
        <Title order={3}>Campaign (pre-landing portabel)</Title>
        <Button onClick={startCreate}>Tambah</Button>
      </Group>
      <Table striped highlightOnHover data-testid="campaigns-table">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>slug</Table.Th>
            <Table.Th>nama</Table.Th>
            <Table.Th>service</Table.Th>
            <Table.Th>origins</Table.Th>
            <Table.Th>status</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(list.data ?? []).map((c) => (
            <Table.Tr key={c.id}>
              <Table.Td>{c.slug}</Table.Td>
              <Table.Td>{c.name}</Table.Td>
              <Table.Td>{c.service}</Table.Td>
              <Table.Td>{(c.allowed_origins ?? []).length}</Table.Td>
              <Table.Td>{c.status}</Table.Td>
              <Table.Td>
                <Button size="xs" variant="light" onClick={() => startEdit(c)}>
                  Edit
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

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
