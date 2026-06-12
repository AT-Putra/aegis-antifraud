import { Badge, Button, Code, Group, Stack, Table, Text, Title } from "@mantine/core";

import { useActivateModel, useModels, useRetrain } from "../hooks/admin";
import { formatTs } from "../lib/tz";

export function ModelsPage() {
  const list = useModels();
  const activate = useActivateModel();
  const retrain = useRetrain();

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={3}>Model & retraining</Title>
        <Button onClick={() => retrain.mutate()} loading={retrain.isPending}>
          Trigger retrain
        </Button>
      </Group>
      <Text c="dimmed" size="sm">
        Aktivasi = approval admin; efektif setelah restart API (hot-reload = masa depan).
      </Text>
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
    </Stack>
  );
}
