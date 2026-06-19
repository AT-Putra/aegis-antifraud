// Bar filter analitik berjenjang service→campaign→source→pub_id + rentang tanggal + tz.
// Polish 2026-06-13: field berlabel+berikon, rentang via @mantine/dates DateTimePicker,
// tombol bersih per-field + reset semua + indikator jumlah filter aktif.
// aria-label dipertahankan agar kontrak test FE tetap utuh.
import { Badge, Button, Card, CloseButton, Group, SimpleGrid, Text, TextInput } from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { IconAdjustmentsHorizontal, IconFilterOff } from "@tabler/icons-react";

import type { AnalyticsFilters } from "../api/types";
import { ServiceCampaignPicker } from "./ServiceCampaignPicker";

// service & campaign kini dropdown chained (ServiceCampaignPicker). source & pub_id tetap
// teks bebas (bukan entitas terdaftar).
const TEXT_FIELDS: { key: keyof AnalyticsFilters; label: string; placeholder: string }[] = [
  { key: "source", label: "source", placeholder: "sumber iklan" },
  { key: "pub_id", label: "pub_id", placeholder: "id publisher" },
];

// DateTimePicker (Mantine 8) memberi string "YYYY-MM-DD HH:mm:ss"; samakan ke ISO-naive
// ("…T…") agar format wire ke backend identik dengan datetime-local lama.
const toWire = (v: string | null) => (v ? v.replace(" ", "T") : null);

export function FilterBar({
  value,
  onChange,
}: {
  value: AnalyticsFilters;
  onChange: (next: AnalyticsFilters) => void;
}) {
  const setText =
    (k: keyof AnalyticsFilters) => (e: React.ChangeEvent<HTMLInputElement>) =>
      onChange({ ...value, [k]: e.currentTarget.value || null });
  const clear = (k: keyof AnalyticsFilters) => () => onChange({ ...value, [k]: null });

  const activeKeys = (["service", "campaign", "source", "pub_id", "from", "to"] as const).filter(
    (k) => value[k],
  );
  const reset = () =>
    onChange({ tz: value.tz, service: null, campaign: null, source: null, pub_id: null, from: null, to: null });

  return (
    <Card padding="md" mb="md">
      <Group justify="space-between" mb="sm">
        <Group gap="xs">
          <IconAdjustmentsHorizontal size={18} stroke={1.8} />
          <Text fw={600} size="sm">
            Filter
          </Text>
          {activeKeys.length > 0 && (
            <Badge variant="light" size="sm">
              {activeKeys.length} aktif
            </Badge>
          )}
        </Group>
        <Button
          variant="subtle"
          size="xs"
          color="gray"
          leftSection={<IconFilterOff size={14} />}
          onClick={reset}
          disabled={activeKeys.length === 0}
        >
          Reset
        </Button>
      </Group>

      {/* Grid responsif: tiap field mengisi penuh selnya & reflow mengikuti lebar layar
          (1 kolom di ponsel → 6 kolom di layar lebar), tak lagi menggerombol ke kiri. */}
      <SimpleGrid cols={{ base: 1, xs: 2, sm: 3, lg: 6 }} spacing="sm" verticalSpacing="sm">
        <ServiceCampaignPicker
          service={value.service}
          campaign={value.campaign}
          onChange={(sc) => onChange({ ...value, service: sc.service, campaign: sc.campaign })}
          width="100%"
        />
        {TEXT_FIELDS.map((f) => (
          <TextInput
            key={f.key}
            label={f.label}
            aria-label={f.key}
            placeholder={f.placeholder}
            value={(value[f.key] as string) ?? ""}
            onChange={setText(f.key)}
            rightSection={
              value[f.key] ? <CloseButton size="sm" aria-label={`bersihkan ${f.key}`} onClick={clear(f.key)} /> : null
            }
          />
        ))}
        <DateTimePicker
          label="Dari"
          aria-label="from"
          placeholder="awal rentang"
          clearable
          value={value.from ?? null}
          onChange={(v) => onChange({ ...value, from: toWire(v) })}
        />
        <DateTimePicker
          label="Sampai"
          aria-label="to"
          placeholder="akhir rentang"
          clearable
          value={value.to ?? null}
          onChange={(v) => onChange({ ...value, to: toWire(v) })}
        />
      </SimpleGrid>
    </Card>
  );
}
