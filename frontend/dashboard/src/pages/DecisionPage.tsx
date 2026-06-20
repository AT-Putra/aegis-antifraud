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
  CopyButton,
  Grid,
  Group,
  Progress,
  Stack,
  Table,
  Text,
  TextInput,
  ThemeIcon,
  Title,
} from "@mantine/core";
import {
  IconActivity,
  IconAlertTriangle,
  IconCheck,
  IconCode,
  IconCopy,
  IconCpu,
  IconDeviceMobile,
  IconInfoCircle,
  IconRoute,
  IconScale,
  IconShieldLock,
  IconWorld,
  type Icon,
} from "@tabler/icons-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import type { Explainability } from "../api/types";
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

const n3 = (v: number | null | undefined) => (typeof v === "number" ? v.toFixed(3) : "—");

// Tombol salin JSON ke clipboard (F-11). Diletakkan di dalam panel agar tak memicu toggle
// accordion. Feedback visual: "Salin JSON" → "Tersalin" (teal) selama timeout.
function CopyJsonButton({ value, label, testId }: { value: string; label: string; testId: string }) {
  return (
    <CopyButton value={value} timeout={1500}>
      {({ copied, copy }) => (
        <Button
          size="xs"
          variant="light"
          color={copied ? "teal" : "indigo"}
          leftSection={copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
          onClick={copy}
          aria-label={label}
          data-testid={testId}
        >
          {copied ? "Tersalin" : "Salin JSON"}
        </Button>
      )}
    </CopyButton>
  );
}

// Penjelasan audit-grade: kenapa skor rules tersusun begitu + komposisi final_score.
function ExplainabilitySection({ ex }: { ex: Explainability }) {
  if (!ex.available) {
    return (
      <Alert color="gray" icon={<IconInfoCircle size={16} />} data-testid="explain-unavailable">
        Penjelasan rinci tak tersedia untuk keputusan ini (data lama/terdegradasi). Lihat skor
        breakdown agregat di atas.
      </Alert>
    );
  }
  const rules = ex.rules;
  const blend = ex.blend;
  const hardForced = rules?.applied_mode === "hard_rule";
  const degraded = ex.feature_source && ex.feature_source !== "stored_features";

  return (
    <Stack data-testid="explainability">
      {ex.rationale && (
        <Alert color={blend?.decision === "block" ? "red" : "teal"} icon={<IconScale size={16} />}>
          {ex.rationale}
        </Alert>
      )}

      {hardForced && (
        <Alert color="red" icon={<IconShieldLock size={16} />} data-testid="hard-rule-alert">
          Diblokir oleh <b>hard-rule</b>: {rules?.hard_rules_triggered.join(", ")}. Skor model
          diabaikan (block paksa) — skor formula tetap ditampilkan sebagai konteks.
        </Alert>
      )}

      {degraded && (
        <Alert color="yellow" icon={<IconAlertTriangle size={16} />} data-testid="feature-source-warning">
          <Text size="sm" fw={600} mb={4}>
            Fitur direkonstruksi ({ex.feature_source})
          </Text>
          {(ex.warnings ?? []).map((w, i) => (
            <Text size="sm" key={i}>
              • {w}
            </Text>
          ))}
        </Alert>
      )}

      {rules && (
        <SectionCard icon={IconActivity} title="Penjelasan skor rules">
          <Stack gap="sm">
            <Code block>{rules.formula}</Code>
            <Table withTableBorder withColumnBorders striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Faktor</Table.Th>
                  <Table.Th>Nilai</Table.Th>
                  <Table.Th>Bobot</Table.Th>
                  <Table.Th>Kontribusi</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {rules.factors.map((f) => (
                  <Table.Tr key={f.name}>
                    <Table.Td>{f.label}</Table.Td>
                    <Table.Td>{n3(f.value)}</Table.Td>
                    <Table.Td>{f.weight}</Table.Td>
                    <Table.Td fw={f.contribution > 0 ? 600 : 400}>{n3(f.contribution)}</Table.Td>
                  </Table.Tr>
                ))}
                <Table.Tr>
                  <Table.Td colSpan={3} ta="right" fw={600}>
                    Skor formula (soft)
                  </Table.Td>
                  <Table.Td fw={700}>{n3(rules.soft_score)}</Table.Td>
                </Table.Tr>
                <Table.Tr>
                  <Table.Td colSpan={3} ta="right" fw={600}>
                    Skor rules efektif
                  </Table.Td>
                  <Table.Td fw={700}>
                    {n3(rules.effective_score)}
                    {hardForced && (
                      <Badge color="red" variant="light" ml="xs" size="sm">
                        hard-rule
                      </Badge>
                    )}
                  </Table.Td>
                </Table.Tr>
              </Table.Tbody>
            </Table>
            <Group gap="xs" wrap="wrap">
              <Text size="xs" c="dimmed">
                Hard-rule aktif:
              </Text>
              {rules.hard_rules_enabled.map((r) => (
                <Badge
                  key={r}
                  size="sm"
                  variant="light"
                  color={rules.hard_rules_triggered.includes(r) ? "red" : "gray"}
                >
                  {r}
                </Badge>
              ))}
            </Group>
          </Stack>
        </SectionCard>
      )}

      {blend && (
        <SectionCard icon={IconScale} title="Komposisi skor akhir">
          <Stack gap="sm">
            <Table withTableBorder withColumnBorders striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Komponen</Table.Th>
                  <Table.Th>Skor</Table.Th>
                  <Table.Th>Bobot</Table.Th>
                  <Table.Th>Bobot ternorm.</Table.Th>
                  <Table.Th>Kontribusi</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {blend.components.map((c) => (
                  <Table.Tr key={c.name} c={c.applied ? undefined : "dimmed"}>
                    <Table.Td>
                      {c.label}
                      {!c.applied && (
                        <Badge color="gray" variant="light" ml="xs" size="xs">
                          tak dipakai
                        </Badge>
                      )}
                    </Table.Td>
                    <Table.Td>{n3(c.score)}</Table.Td>
                    <Table.Td>{c.weight}</Table.Td>
                    <Table.Td>{n3(c.normalized_weight)}</Table.Td>
                    <Table.Td fw={c.applied ? 600 : 400}>{n3(c.contribution)}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
            <Group justify="space-between">
              <Text size="sm" c="dimmed">
                mode: <Code>{blend.mode}</Code>
              </Text>
              <Group gap={6} align="center">
                <Text size="sm">
                  skor akhir <b>{n3(blend.final_score)}</b>{" "}
                  {blend.decision === "block" ? "≥" : "<"} ambang {blend.threshold} →
                </Text>
                <DecisionBadge decision={blend.decision} />
              </Group>
            </Group>
          </Stack>
        </SectionCard>
      )}

      <Alert color="blue" icon={<IconInfoCircle size={16} />}>
        {ex.models?.note ??
          "Skor IF/LightGBM ditampilkan sebagai skalar × bobot blend. Atribusi per-fitur (SHAP) belum tersedia."}
      </Alert>
    </Stack>
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
  const signalsJson = JSON.stringify(d.signals ?? {}, null, 2);
  const rawJson = JSON.stringify(d, null, 2);

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
                { label: "IP address", value: fmt(ip.ip_address) },
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

      {/* Penjelasan audit-grade (03 §7) — kenapa skor & keputusan begini. */}
      {d.explainability && <ExplainabilitySection ex={d.explainability} />}

      {/* Fallback JSON mentah — sinyal free-form & seluruh objek (defensif). */}
      <Accordion variant="separated" chevronPosition="left">
        <Accordion.Item value="signals">
          <Accordion.Control icon={<IconCode size={16} />}>Signals (data mentah)</Accordion.Control>
          <Accordion.Panel>
            <Group justify="flex-end" mb="xs">
              <CopyJsonButton value={signalsJson} label="Salin signals JSON" testId="copy-signals" />
            </Group>
            <Code block>{signalsJson}</Code>
          </Accordion.Panel>
        </Accordion.Item>
        <Accordion.Item value="raw">
          <Accordion.Control icon={<IconCode size={16} />}>Seluruh respons (JSON mentah)</Accordion.Control>
          <Accordion.Panel>
            <Group justify="flex-end" mb="xs">
              <CopyJsonButton value={rawJson} label="Salin seluruh respons JSON" testId="copy-raw" />
            </Group>
            <Code block>{rawJson}</Code>
          </Accordion.Panel>
        </Accordion.Item>
      </Accordion>

      {q.data.decision === "unknown" && (
        <Alert color="yellow">Data OLAP tak lengkap untuk trx ini; sebagian detail mungkin kosong.</Alert>
      )}
    </Stack>
  );
}
