// Detail keputusan (F-11): ringkasan + skor breakdown, IP intel, device, atribusi, outcome
// dirender TERSTRUKTUR (key-value/badge) + fallback JSON mentah (collapsible).
// + flag feedback human/robot (F-09). Field mengacu ke analytics_repo.decision_detail (03 §7).
import {
  Accordion,
  Alert,
  Badge,
  Button,
  Card,
  Code,
  Grid,
  Group,
  Progress,
  Stack,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconActivity,
  IconCode,
  IconCpu,
  IconDeviceMobile,
  IconRoute,
  IconWorld,
  type Icon,
} from "@tabler/icons-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { DecisionBadge } from "../components/DecisionBadge";
import { KeyValue, fmt } from "../components/KeyValue";
import { ErrorState, LoadingRows } from "../components/StateViews";
import { useSubmitFeedback } from "../hooks/admin";
import { useDecision } from "../hooks/queries";
import { weboptinColor } from "../lib/decision";

function SectionCard({ icon: Ico, title, children }: { icon: Icon; title: string; children: React.ReactNode }) {
  return (
    <Card padding="md" h="100%">
      <Group gap="xs" mb="sm">
        <ThemeIcon variant="light" color="indigo" size="sm" radius="md">
          <Ico size={15} stroke={1.8} />
        </ThemeIcon>
        <Text fw={600}>{title}</Text>
      </Group>
      {children}
    </Card>
  );
}

// Sub-skor (0..1) → bar. Nilai null → "—".
function ScoreBar({ label, value }: { label: string; value: unknown }) {
  const num = typeof value === "number" ? value : null;
  return (
    <Stack gap={4}>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">
          {label}
        </Text>
        <Text size="sm" fw={600}>
          {num == null ? "—" : num.toFixed(3)}
        </Text>
      </Group>
      <Progress value={num == null ? 0 : Math.min(100, Math.max(0, num * 100))} color="indigo" size="sm" radius="xl" />
    </Stack>
  );
}

function FlagCard({ trxId }: { trxId: string }) {
  const submit = useSubmitFeedback();
  const [note, setNote] = useState("");
  const flag = (label: "human" | "robot") =>
    submit.mutate({ trx_id: trxId, flagged_label: label, note: note || undefined });
  return (
    <Card padding="md" data-testid="flag-card">
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

  if (q.isLoading) return <LoadingRows rows={4} />;
  if (q.isError || !q.data) return <ErrorState label="Keputusan tidak ditemukan." />;
  const d = q.data;

  const ip = d.ip_intelligence ?? {};
  const dev = d.device_info ?? {};
  const outcome = d.outcome ?? {};
  const threshold = typeof outcome.threshold_used === "number" ? outcome.threshold_used : null;

  return (
    <Stack>
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <Stack gap={4}>
          <Title order={3}>Keputusan</Title>
          <Text ff="monospace" c="dimmed">
            {d.trx_id}
          </Text>
        </Stack>
        <Group gap="sm" data-testid="decision-meta" align="center">
          <DecisionBadge decision={d.decision} />
          <Text size="sm" c="dimmed">
            skor
          </Text>
          <Text fw={700}>{d.final_score ?? "-"}</Text>
          {threshold != null && (
            <Text size="sm" c="dimmed">
              / ambang {threshold}
            </Text>
          )}
        </Group>
      </Group>

      {/* Atribusi berjenjang service → campaign → source → pub_id */}
      <Card padding="md">
        <Group gap="xs" mb="sm">
          <ThemeIcon variant="light" color="indigo" size="sm" radius="md">
            <IconRoute size={15} stroke={1.8} />
          </ThemeIcon>
          <Text fw={600}>Atribusi</Text>
        </Group>
        <Group gap="xs" wrap="wrap">
          <Badge variant="light">service: {fmt(d.service)}</Badge>
          <Text c="dimmed">›</Text>
          <Badge variant="light">campaign: {fmt(d.campaign)}</Badge>
          <Text c="dimmed">›</Text>
          <Badge variant="light">source: {fmt(d.source)}</Badge>
          <Text c="dimmed">›</Text>
          <Badge variant="light">pub_id: {fmt(d.pub_id)}</Badge>
          <Badge color={weboptinColor(d.weboptin_status)} variant="light" ml="md">
            web-opt-in: {d.weboptin_status ?? "—"}
          </Badge>
        </Group>
      </Card>

      <FlagCard trxId={d.trx_id} />

      <Grid>
        <Grid.Col span={{ base: 12, md: 6 }}>
          <SectionCard icon={IconActivity} title="Score breakdown">
            <Stack gap="sm">
              <ScoreBar label="Rules" value={d.score_breakdown?.rules} />
              <ScoreBar label="Isolation Forest" value={d.score_breakdown?.isolation_forest} />
              <ScoreBar label="LightGBM" value={d.score_breakdown?.lightgbm} />
            </Stack>
          </SectionCard>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <SectionCard icon={IconCpu} title="Outcome">
            <KeyValue
              rows={[
                { label: "Alasan", value: fmt(outcome.reason) },
                { label: "Ambang dipakai", value: fmt(outcome.threshold_used) },
                { label: "Web-opt-in host", value: fmt(d.weboptin_host) },
                { label: "Versi rules", value: fmt(d.rules_version) },
                { label: "Versi model", value: fmt(d.model_version) },
                {
                  label: "Callbacks",
                  value: Array.isArray(outcome.callbacks) ? `${outcome.callbacks.length} entri` : fmt(outcome.callbacks),
                },
              ]}
            />
          </SectionCard>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <SectionCard icon={IconWorld} title="IP intelligence">
            <KeyValue
              rows={[
                { label: "Negara", value: fmt(ip.country) },
                { label: "ASN", value: fmt(ip.asn) },
                { label: "ISP", value: fmt(ip.isp) },
                { label: "Koneksi", value: fmt(ip.connection_type) },
                {
                  label: "VPN / Proxy / Tor",
                  value: ip.vpn_proxy_tor ? <Badge color="red" variant="light">terdeteksi</Badge> : fmt(ip.vpn_proxy_tor),
                },
                { label: "Reputasi IP", value: fmt(ip.ip_reputation) },
              ]}
            />
          </SectionCard>
        </Grid.Col>

        <Grid.Col span={{ base: 12, md: 6 }}>
          <SectionCard icon={IconDeviceMobile} title="Device info">
            <KeyValue
              rows={[
                { label: "Browser", value: fmt(dev.browser) },
                { label: "OS", value: fmt(dev.os) },
                { label: "Tipe perangkat", value: fmt(dev.device_type) },
                { label: "Brand", value: fmt(dev.brand) },
                { label: "Model", value: fmt(dev.model) },
                {
                  label: "WebView",
                  value: dev.is_webview ? <Badge color="orange" variant="light">ya (sinyal risiko)</Badge> : fmt(dev.is_webview),
                },
              ]}
            />
          </SectionCard>
        </Grid.Col>
      </Grid>

      {/* Fallback JSON mentah — sinyal free-form & seluruh objek (defensif). */}
      <Accordion variant="separated" chevronPosition="left">
        <Accordion.Item value="signals">
          <Accordion.Control icon={<IconCode size={16} />}>Signals (data mentah)</Accordion.Control>
          <Accordion.Panel>
            <Code block>{JSON.stringify(d.signals ?? {}, null, 2)}</Code>
          </Accordion.Panel>
        </Accordion.Item>
        <Accordion.Item value="raw">
          <Accordion.Control icon={<IconCode size={16} />}>Seluruh respons (JSON mentah)</Accordion.Control>
          <Accordion.Panel>
            <Code block>{JSON.stringify(d, null, 2)}</Code>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>

      {q.data.decision === "unknown" && (
        <Alert color="yellow">Data OLAP tak lengkap untuk trx ini; sebagian detail mungkin kosong.</Alert>
      )}
    </Stack>
  );
}
