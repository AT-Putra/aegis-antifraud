import { Anchor, Button, Group, Loader, Stack, Table, Text, TextInput } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { DecisionBadge } from "../components/DecisionBadge";
import { PageHeader } from "../components/PageHeader";
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
      <PageHeader
        title="Pencarian"
        description="Telusuri keputusan berdasarkan trx, perangkat, layanan, campaign, atau atribut lain. Klik trx untuk detail."
      />
      <Group gap="xs" wrap="wrap" align="flex-end">
        {FIELDS.map((f) => (
          <TextInput key={f} aria-label={f} placeholder={f} value={draft[f] ?? ""} onChange={set(f)} />
        ))}
        <Button onClick={run} leftSection={<IconSearch size={16} />}>
          Cari
        </Button>
      </Group>

      {q.isFetching ? (
        <Loader />
      ) : active !== null && q.data && q.data.length === 0 ? (
        <Text size="sm" c="dimmed" ta="center" py="xl">
          Tidak ada hasil untuk filter ini.
        </Text>
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
                <Table.Td>
                  <DecisionBadge decision={r.decision} />
                </Table.Td>
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
