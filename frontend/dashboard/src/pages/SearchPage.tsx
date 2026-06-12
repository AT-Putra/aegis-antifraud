import { Anchor, Button, Group, Loader, Stack, Table, TextInput, Title } from "@mantine/core";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useSearch } from "../hooks/queries";
import { formatTs } from "../lib/tz";

const FIELDS = ["trx_id", "device_id", "decision", "service", "campaign", "source", "pub_id", "country", "browser"];

export function SearchPage() {
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [active, setActive] = useState<Record<string, unknown> | null>(null);
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
  };

  return (
    <Stack>
      <Title order={3}>Pencarian</Title>
      <Group gap="xs" wrap="wrap">
        {FIELDS.map((f) => (
          <TextInput key={f} aria-label={f} placeholder={f} value={draft[f] ?? ""} onChange={set(f)} />
        ))}
        <Button onClick={run}>Cari</Button>
      </Group>

      {q.isFetching ? (
        <Loader />
      ) : q.data ? (
        <Table striped highlightOnHover data-testid="results">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>trx_id</Table.Th>
              <Table.Th>decision</Table.Th>
              <Table.Th>service</Table.Th>
              <Table.Th>campaign</Table.Th>
              <Table.Th>waktu</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {q.data.map((r) => (
              <Table.Tr key={r.trx_id}>
                <Table.Td>
                  <Anchor onClick={() => navigate(`/decision/${encodeURIComponent(r.trx_id)}`)}>
                    {r.trx_id}
                  </Anchor>
                </Table.Td>
                <Table.Td>{r.decision}</Table.Td>
                <Table.Td>{r.service}</Table.Td>
                <Table.Td>{r.campaign}</Table.Td>
                <Table.Td>{formatTs(r.ts)}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      ) : null}
    </Stack>
  );
}
