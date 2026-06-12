// Detail keputusan (F-11): skor breakdown, signals, ip, device, atribusi, outcome.
// + flag feedback human/robot (F-09).
import { Alert, Button, Card, Code, Grid, Group, Loader, Stack, Text, TextInput, Title } from "@mantine/core";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { useSubmitFeedback } from "../hooks/admin";
import { useDecision } from "../hooks/queries";

function JsonCard({ title, value }: { title: string; value: unknown }) {
  return (
    <Card withBorder padding="md" radius="md">
      <Text fw={600} mb="xs">
        {title}
      </Text>
      <Code block>{JSON.stringify(value ?? {}, null, 2)}</Code>
    </Card>
  );
}

function FlagCard({ trxId }: { trxId: string }) {
  const submit = useSubmitFeedback();
  const [note, setNote] = useState("");
  const flag = (label: "human" | "robot") =>
    submit.mutate({ trx_id: trxId, flagged_label: label, note: note || undefined });
  return (
    <Card withBorder padding="md" radius="md" data-testid="flag-card">
      <Text fw={600} mb="xs">
        Flag keputusan ini (untuk review admin)
      </Text>
      <Group align="flex-end">
        <TextInput label="Catatan (opsional)" value={note} onChange={(e) => setNote(e.currentTarget.value)} style={{ flex: 1 }} />
        <Button color="teal" variant="light" loading={submit.isPending} onClick={() => flag("human")}>
          Tandai human
        </Button>
        <Button color="red" variant="light" loading={submit.isPending} onClick={() => flag("robot")}>
          Tandai robot
        </Button>
      </Group>
    </Card>
  );
}

export function DecisionPage() {
  const { trxId = "" } = useParams();
  const q = useDecision(trxId);

  if (q.isLoading) return <Loader />;
  if (q.isError || !q.data) return <Alert color="red">Keputusan tidak ditemukan.</Alert>;
  const d = q.data;

  return (
    <Stack>
      <Title order={3}>Keputusan {d.trx_id}</Title>
      <Group gap="lg" wrap="wrap" data-testid="decision-meta">
        <Text>Keputusan: <b>{d.decision}</b></Text>
        <Text>Skor: {d.final_score ?? "-"}</Text>
        <Text>Service: {d.service ?? "-"}</Text>
        <Text>Campaign: {d.campaign ?? "-"}</Text>
        <Text>Source: {d.source ?? "-"}</Text>
        <Text>Pub: {d.pub_id ?? "-"}</Text>
        <Text>Web-opt-in: {d.weboptin_status ?? "-"}</Text>
      </Group>
      <FlagCard trxId={d.trx_id} />
      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}><JsonCard title="Score breakdown" value={d.score_breakdown} /></Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}><JsonCard title="IP intelligence" value={d.ip_intelligence} /></Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}><JsonCard title="Device info" value={d.device_info} /></Grid.Col>
        <Grid.Col span={{ base: 12, md: 6 }}><JsonCard title="Outcome" value={d.outcome} /></Grid.Col>
        <Grid.Col span={12}><JsonCard title="Signals" value={d.signals} /></Grid.Col>
      </Grid>
    </Stack>
  );
}
