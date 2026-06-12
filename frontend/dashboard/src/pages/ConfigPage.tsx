import { Alert, Button, Card, Group, JsonInput, NumberInput, Stack, Table, Text, Title } from "@mantine/core";
import { useEffect, useState } from "react";

import { fetchConfigVersion, useConfig, useConfigVersions, usePutConfig } from "../hooks/admin";
import { formatTs } from "../lib/tz";

export function ConfigPage() {
  const cfg = useConfig();
  const versions = useConfigVersions();
  const put = usePutConfig();

  const [params, setParams] = useState("{}");
  const [blend, setBlend] = useState("{}");
  const [threshold, setThreshold] = useState<number>(0.5);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (cfg.data) {
      setParams(JSON.stringify(cfg.data.params ?? {}, null, 2));
      setBlend(JSON.stringify(cfg.data.blend_weights ?? {}, null, 2));
      setThreshold(cfg.data.threshold);
    }
  }, [cfg.data]);

  const loadVersion = async (v: number) => {
    setErr(null);
    const data = await fetchConfigVersion(v);
    setParams(JSON.stringify(data.params ?? {}, null, 2));
    setBlend(JSON.stringify(data.blend_weights ?? {}, null, 2));
    setThreshold(data.threshold);
  };

  const save = () => {
    setErr(null);
    try {
      put.mutate({
        params: JSON.parse(params),
        threshold,
        blend_weights: JSON.parse(blend),
      });
    } catch {
      setErr("JSON params/blend_weights tidak valid.");
    }
  };

  return (
    <Stack>
      <Title order={3}>Config scoring</Title>
      <Card withBorder padding="md" radius="md">
        <Stack>
          <Text c="dimmed" size="sm">
            Versi aktif: {cfg.data?.version ?? "-"}
          </Text>
          <NumberInput label="Threshold" value={threshold} onChange={(v) => setThreshold(Number(v))} step={0.05} min={0} max={1} decimalScale={3} />
          <JsonInput label="Params (JSON)" value={params} onChange={setParams} autosize minRows={4} formatOnBlur validationError="JSON tidak valid" />
          <JsonInput label="Blend weights (JSON)" value={blend} onChange={setBlend} autosize minRows={2} formatOnBlur validationError="JSON tidak valid" />
          {cfg.data?.guidelines && Object.keys(cfg.data.guidelines).length > 0 && (
            <JsonInput label="Guidelines (default+range, read-only)" value={JSON.stringify(cfg.data.guidelines, null, 2)} readOnly autosize minRows={2} />
          )}
          {err && <Alert color="red">{err}</Alert>}
          <Group>
            <Button onClick={save} loading={put.isPending}>
              Simpan (versi baru + aktif)
            </Button>
          </Group>
        </Stack>
      </Card>

      <Card withBorder padding="md" radius="md">
        <Text fw={600} mb="sm">
          Riwayat versi (rollback: Muat → Simpan)
        </Text>
        <Table data-testid="config-versions">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>versi</Table.Th>
              <Table.Th>dibuat</Table.Th>
              <Table.Th>aktif</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {(versions.data ?? []).map((v) => (
              <Table.Tr key={v.version}>
                <Table.Td>{v.version}</Table.Td>
                <Table.Td>{formatTs(v.created_at)}</Table.Td>
                <Table.Td>{v.active ? "✓" : ""}</Table.Td>
                <Table.Td>
                  <Button size="xs" variant="light" onClick={() => loadVersion(v.version)}>
                    Muat
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Card>
    </Stack>
  );
}
