import {
  Badge,
  Button,
  Group,
  Modal,
  MultiSelect,
  Select,
  Stack,
  Switch,
  Textarea,
  TextInput,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconPlus } from "@tabler/icons-react";
import { DataTable } from "mantine-datatable";
import { useState } from "react";

import type { CampaignOut, RegistryOption } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { QuickFilter } from "../components/QuickFilter";
import { useClientTable } from "../lib/clientTable";
import { COUNTRY_OPTIONS } from "../lib/countries";
import { useCampaigns, useSaveCampaign } from "../hooks/admin";
import { useServiceOptions } from "../hooks/queries";

interface Draft {
  id?: string;
  slug: string;
  name: string;
  service: string;
  origins: string; // satu origin per baris
  countries: string[]; // kode ISO alpha-2, atau ["ALL"] = tanpa batas geo (F-17)
  homeCountry: string | null; // ekspektasi negara (ADR-020); null = tanpa ekspektasi
  expectCarrier: boolean; // harap IP operator seluler (ADR-020)
  status: "active" | "inactive";
}
const ALL = "ALL";
const EMPTY: Draft = {
  slug: "", name: "", service: "", origins: "", countries: [ALL],
  homeCountry: null, expectCarrier: false, status: "active",
};

// ALL + daftar negara. ALL = pilihan eksplisit "tanpa batas" (disimpan sbg [] di backend).
const COUNTRY_DATA = [
  { value: ALL, label: "ALL — semua negara (tanpa batas)" },
  ...COUNTRY_OPTIONS,
];

function parseOrigins(s: string): string[] {
  return s.split("\n").map((x) => x.trim()).filter(Boolean);
}

// allowed_countries backend ([] = ALL) → state form (["ALL"] = ALL, mandatory non-kosong).
function toDraftCountries(codes: string[]): string[] {
  return codes.length === 0 ? [ALL] : codes;
}

function serviceData(opts: RegistryOption[] | undefined) {
  return (opts ?? []).map((o) => ({
    value: o.slug,
    label: o.status === "active" ? `${o.name} (${o.slug})` : `${o.name} (${o.slug}) — nonaktif`,
  }));
}

export function CampaignsPage() {
  const list = useCampaigns();
  const services = useServiceOptions();
  const save = useSaveCampaign();
  const [opened, { open, close }] = useDisclosure(false);
  const [d, setD] = useState<Draft>(EMPTY);
  const editing = !!d.id;

  const t = useClientTable<CampaignOut>(list.data ?? [], {
    initialSort: { columnAccessor: "slug", direction: "asc" },
    filterKeys: ["slug", "name", "service", "status"],
  });

  const startCreate = () => {
    setD(EMPTY);
    open();
  };
  const startEdit = (c: CampaignOut) => {
    setD({
      id: c.id, slug: c.slug, name: c.name, service: c.service,
      origins: (c.allowed_origins ?? []).join("\n"),
      countries: toDraftCountries(c.allowed_countries ?? []),
      homeCountry: c.home_country ?? null,
      expectCarrier: c.expect_mobile_carrier ?? false,
      status: c.status,
    });
    open();
  };

  // ALL ⇄ negara: kosong → kembali ke ALL (mandatory); pilih ALL → reset ke ALL saja;
  // pilih negara saat ALL aktif → buang ALL.
  const onCountries = (vals: string[]) => {
    let next: string[];
    if (vals.length === 0) next = [ALL];
    else if (vals.includes(ALL) && !d.countries.includes(ALL)) next = [ALL];
    else if (vals.includes(ALL) && vals.length > 1) next = vals.filter((v) => v !== ALL);
    else next = vals;
    setD({ ...d, countries: next });
  };

  const submit = () => {
    const countries = d.countries.includes(ALL) ? [] : d.countries; // ["ALL"] → [] (= ALL)
    const geo = { home_country: d.homeCountry || null, expect_mobile_carrier: d.expectCarrier };
    const body: Record<string, unknown> = editing
      ? { name: d.name, allowed_origins: parseOrigins(d.origins), allowed_countries: countries, status: d.status, ...geo }
      : { slug: d.slug, name: d.name, service: d.service, allowed_origins: parseOrigins(d.origins), allowed_countries: countries, ...geo };
    save.mutate({ id: d.id, body }, { onSuccess: close });
  };

  return (
    <Stack>
      <PageHeader
        title="Campaign (pre-landing portabel)"
        description="Tiap campaign = satu pre-landing dengan whitelist origin (CORS) sendiri."
        actions={
          <Button leftSection={<IconPlus size={16} />} onClick={startCreate}>
            Tambah
          </Button>
        }
      />
      <Group justify="flex-end">
        <QuickFilter value={t.query} onChange={t.setQuery} placeholder="Filter campaign…" testid="campaigns-filter" />
      </Group>
      <DataTable<CampaignOut>
        data-testid="campaigns-table"
        minHeight={180}
        withTableBorder
        borderRadius="md"
        striped
        highlightOnHover
        records={t.paged}
        idAccessor="id"
        fetching={list.isLoading}
        noRecordsText="Belum ada campaign"
        page={t.page}
        onPageChange={t.setPage}
        totalRecords={t.total}
        recordsPerPage={t.pageSize}
        sortStatus={t.sort}
        onSortStatusChange={t.setSort}
        columns={[
          { accessor: "slug", sortable: true },
          { accessor: "name", title: "nama", sortable: true },
          { accessor: "service", sortable: true },
          {
            accessor: "allowed_origins",
            title: "origins",
            render: (c) => (
              <Badge variant="light" color="gray">
                {(c.allowed_origins ?? []).length} origin
              </Badge>
            ),
          },
          {
            accessor: "allowed_countries",
            title: "negara",
            render: (c) =>
              (c.allowed_countries ?? []).length === 0 ? (
                <Badge variant="light" color="teal">ALL</Badge>
              ) : (
                <Badge variant="light" color="blue">
                  {(c.allowed_countries ?? []).length} negara
                </Badge>
              ),
          },
          {
            accessor: "status",
            sortable: true,
            render: (c) => (
              <Badge color={c.status === "active" ? "teal" : "gray"} variant="light">
                {c.status}
              </Badge>
            ),
          },
          {
            accessor: "actions",
            title: "",
            textAlign: "right",
            render: (c) => (
              <Button size="xs" variant="light" onClick={() => startEdit(c)}>
                Edit
              </Button>
            ),
          },
        ]}
      />

      <Modal opened={opened} onClose={close} title={editing ? "Edit campaign" : "Tambah campaign"}>
        <Stack>
          <TextInput label="Slug" value={d.slug} disabled={editing} onChange={(e) => setD({ ...d, slug: e.currentTarget.value })} />
          <TextInput label="Nama" value={d.name} onChange={(e) => setD({ ...d, name: e.currentTarget.value })} />
          <Select
            label="Service (slug)"
            placeholder={services.isLoading ? "memuat…" : "pilih service"}
            data={serviceData(services.data)}
            value={d.service || null}
            onChange={(v) => setD({ ...d, service: v ?? "" })}
            searchable
            disabled={editing}
            nothingFoundMessage="Tidak ada service"
          />
          <Textarea label="Allowed origins (satu per baris)" autosize minRows={2} value={d.origins} onChange={(e) => setD({ ...d, origins: e.currentTarget.value })} />
          <MultiSelect
            label="Negara diizinkan (web-opt-in)"
            description="ALL = semua negara (tanpa batas). Pilih satu/lebih negara untuk membatasi akses ke negara tsb."
            placeholder="Cari negara…"
            data={COUNTRY_DATA}
            value={d.countries}
            onChange={onCountries}
            searchable
            hidePickedOptions
            nothingFoundMessage="Negara tidak ditemukan"
            maxDropdownHeight={260}
          />
          <Select
            label="Negara asal diharapkan (home country)"
            description="Ekspektasi geo (ADR-020): IP di luar negara ini → sinyal soft campaign_geo_mismatch (bukan blokir). Kosong = tanpa ekspektasi."
            placeholder="(tanpa ekspektasi)"
            data={COUNTRY_OPTIONS}
            value={d.homeCountry}
            onChange={(v) => setD({ ...d, homeCountry: v })}
            searchable
            clearable
            nothingFoundMessage="Negara tidak ditemukan"
            maxDropdownHeight={260}
          />
          <Switch
            label="Harapkan IP operator seluler"
            description="Untuk campaign billing operator (mis. Telkomsel): IP non-seluler → sinyal soft campaign_geo_mismatch."
            checked={d.expectCarrier}
            onChange={(e) => setD({ ...d, expectCarrier: e.currentTarget.checked })}
          />
          {editing && (
            <Select label="Status" data={["active", "inactive"]} value={d.status} onChange={(v) => setD({ ...d, status: (v as "active" | "inactive") ?? "active" })} />
          )}
          <Button onClick={submit} loading={save.isPending}>
            Simpan
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
