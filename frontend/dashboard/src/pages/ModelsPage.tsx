import { Badge, Button, Code, Stack, Table } from "@mantine/core";
import { IconReload } from "@tabler/icons-react";

import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/StateViews";
import { useActivateModel, useModels, useRetrain } from "../hooks/admin";
import { formatTs } from "../lib/tz";

export function ModelsPage() {
  const list = useModels();
  const activate = useActivateModel();
  const retrain = useRetrain();

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
      <Table striped data-testid="models-table">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>versi</Table.Th>
            <Table.Th>algoritma</Table.Th>
            <Table.Th>dilatih</Table.Th>
            <Table.Th>metrics</Table.Th>
            <Table.Th>aktif</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(list.data ?? []).map((m) => (
            <Table.Tr key={m.id}>
              <Table.Td>{m.version}</Table.Td>
              <Table.Td>{m.algorithm}</Table.Td>
              <Table.Td>{m.trained_at ? formatTs(m.trained_at) : "-"}</Table.Td>
              <Table.Td>
                <Code>{JSON.stringify(m.metrics ?? {})}</Code>
              </Table.Td>
              <Table.Td>{m.active ? <Badge color="teal">aktif</Badge> : ""}</Table.Td>
              <Table.Td>
                {!m.active && (
                  <Button size="xs" variant="light" onClick={() => activate.mutate(m.id)}>
                    Aktifkan
                  </Button>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      {(list.data ?? []).length === 0 && !list.isLoading && (
        <EmptyState label="Belum ada model" hint="Jalankan retraining untuk menghasilkan versi model pertama." />
      )}
    </Stack>
  );
}
