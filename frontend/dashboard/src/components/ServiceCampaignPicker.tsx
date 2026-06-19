// Dropdown chained service → campaign (gaya Select2: searchable + clearable).
// Service & campaign adalah entitas terdaftar → dipilih dari daftar, bukan diketik bebas.
// Campaign hanya menampilkan campaign milik service terpilih (child dari service).
// Daftar mencakup slug nonaktif (diberi penanda) agar filter atas data historis tetap mungkin.
import { Select } from "@mantine/core";

import type { RegistryOption } from "../api/types";
import { useCampaignOptions, useServiceOptions } from "../hooks/queries";

// value = slug (sesuai kontrak filter analytics ?service=&campaign=); label = nama + slug.
function toData(opts: RegistryOption[] | undefined) {
  return (opts ?? []).map((o) => ({
    value: o.slug,
    label: o.status === "active" ? `${o.name} (${o.slug})` : `${o.name} (${o.slug}) — nonaktif`,
  }));
}

export function ServiceCampaignPicker({
  service,
  campaign,
  onChange,
  width = 220,
}: {
  service: string | null | undefined;
  campaign: string | null | undefined;
  onChange: (next: { service: string | null; campaign: string | null }) => void;
  width?: number | string;
}) {
  const services = useServiceOptions();
  const campaigns = useCampaignOptions(service);

  return (
    <>
      <Select
        label="service"
        aria-label="service"
        placeholder={services.isLoading ? "memuat…" : "pilih service"}
        data={toData(services.data)}
        value={service ?? null}
        onChange={(v) => onChange({ service: v, campaign: null })} // reset campaign saat service ganti
        searchable
        clearable
        nothingFoundMessage="Tidak ada service"
        w={width}
      />
      <Select
        label="campaign"
        aria-label="campaign"
        placeholder={!service ? "pilih service dulu" : campaigns.isLoading ? "memuat…" : "pilih campaign"}
        data={toData(campaigns.data)}
        value={campaign ?? null}
        onChange={(v) => onChange({ service: service ?? null, campaign: v })}
        searchable
        clearable
        disabled={!service}
        nothingFoundMessage="Tidak ada campaign untuk service ini"
        w={width}
      />
    </>
  );
}
