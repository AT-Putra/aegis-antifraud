import { Alert, Button, Card, Group, JsonInput, NumberInput, Stack, Text } from "@mantine/core";
import { DataTable } from "mantine-datatable";
import { useEffect, useState } from "react";

import type { ConfigVersionItem } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { useClientTable } from "../lib/clientTable";
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

  const t = useClientTable<ConfigVersionItem>(versions.data ?? [], {
    initialSort: { columnAccessor: "version", direction: "desc" },
  });

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
      <PageHeader
        title="Config scoring"
        description="Atur threshold, params rules, dan bobot blend. Setiap simpan membuat versi baru yang aktif; rollback via riwayat."
      />
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
        <DataTable<ConfigVersionItem>
          data-testid="config-versions"
          minHeight={160}
          withTableBorder
          borderRadius="md"
          striped
          highlightOnHover
          records={t.paged}
          idAccessor="version"
          fetching={versions.isLoading}
          noRecordsText="Belum ada versi"
          page={t.page}
          onPageChange={t.setPage}
          totalRecords={t.total}
          recordsPerPage={t.pageSize}
          sortStatus={t.sort}
          onSortStatusChange={t.setSort}
          columns={[
            { accessor: "version", title: "versi", sortable: true },
            {
              accessor: "created_at",
              title: "dibuat",
              sortable: true,
              render: (v) => formatTs(v.created_at),
            },
            {
              accessor: "active",
              title: "aktif",
              sortable: true,
              render: (v) => (v.active ? "✓" : ""),
            },
            {
              accessor: "actions",
              title: "",
              textAlign: "right",
              render: (v) => (
                <Button size="xs" variant="light" onClick={() => loadVersion(v.version)}>
                  Muat
                </Button>
              ),
            },
          ]}
        />
      </Card>
    </Stack>
  );
}
