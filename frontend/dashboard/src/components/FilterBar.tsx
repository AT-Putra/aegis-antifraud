// Bar filter analitik berjenjang service→campaign→source→pub_id + rentang tanggal + tz.
import { Group, TextInput } from "@mantine/core";

import type { AnalyticsFilters } from "../api/types";

export function FilterBar({
  value,
  onChange,
}: {
  value: AnalyticsFilters;
  onChange: (next: AnalyticsFilters) => void;
}) {
  const set = (k: keyof AnalyticsFilters) => (e: React.ChangeEvent<HTMLInputElement>) =>
    onChange({ ...value, [k]: e.currentTarget.value || null });

  return (
    <Group gap="xs" wrap="wrap">
      <TextInput aria-label="service" placeholder="service" value={value.service ?? ""} onChange={set("service")} />
      <TextInput aria-label="campaign" placeholder="campaign" value={value.campaign ?? ""} onChange={set("campaign")} />
      <TextInput aria-label="source" placeholder="source" value={value.source ?? ""} onChange={set("source")} />
      <TextInput aria-label="pub_id" placeholder="pub_id" value={value.pub_id ?? ""} onChange={set("pub_id")} />
      <TextInput aria-label="from" type="datetime-local" value={value.from ?? ""} onChange={set("from")} />
      <TextInput aria-label="to" type="datetime-local" value={value.to ?? ""} onChange={set("to")} />
    </Group>
  );
}
