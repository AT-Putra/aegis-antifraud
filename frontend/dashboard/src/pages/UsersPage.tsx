import { Badge, Button, Group, Modal, PasswordInput, Select, Stack, Switch, TextInput } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconPlus } from "@tabler/icons-react";
import { DataTable } from "mantine-datatable";
import { useState } from "react";

import type { Role, UserOut } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { QuickFilter } from "../components/QuickFilter";
import { useClientTable } from "../lib/clientTable";
import { useSaveUser, useUsers } from "../hooks/admin";

interface Draft {
  id?: string;
  username: string;
  password: string;
  role: Role;
  active: boolean;
}
const EMPTY: Draft = { username: "", password: "", role: "user", active: true };

export function UsersPage() {
  const list = useUsers();
  const save = useSaveUser();
  const [opened, { open, close }] = useDisclosure(false);
  const [d, setD] = useState<Draft>(EMPTY);
  const editing = !!d.id;

  const t = useClientTable<UserOut>(list.data ?? [], {
    initialSort: { columnAccessor: "username", direction: "asc" },
    filterKeys: ["username", "role"],
  });

  const startCreate = () => {
    setD(EMPTY);
    open();
  };
  const startEdit = (u: UserOut) => {
    setD({ id: u.id, username: u.username, password: "", role: u.role, active: u.active });
    open();
  };
  const submit = () => {
    const body: Record<string, unknown> = editing
      ? { role: d.role, active: d.active }
      : { username: d.username, password: d.password, role: d.role };
    if (editing && d.password) body.password = d.password;
    save.mutate({ id: d.id, body }, { onSuccess: close });
  };

  return (
    <Stack>
      <PageHeader
        title="Users"
        description="Kelola akun dashboard & perannya (admin / user)."
        actions={
          <Button leftSection={<IconPlus size={16} />} onClick={startCreate}>
            Tambah
          </Button>
        }
      />
      <Group justify="flex-end">
        <QuickFilter value={t.query} onChange={t.setQuery} placeholder="Filter user…" testid="users-filter" />
      </Group>
      <DataTable<UserOut>
        data-testid="users-table"
        minHeight={180}
        withTableBorder
        borderRadius="md"
        striped
        highlightOnHover
        records={t.paged}
        idAccessor="id"
        fetching={list.isLoading}
        noRecordsText="Belum ada user"
        page={t.page}
        onPageChange={t.setPage}
        totalRecords={t.total}
        recordsPerPage={t.pageSize}
        sortStatus={t.sort}
        onSortStatusChange={t.setSort}
        columns={[
          { accessor: "username", sortable: true },
          {
            accessor: "role",
            sortable: true,
            render: (u) => (
              <Badge variant="light" color={u.role === "admin" ? "indigo" : "gray"}>
                {u.role}
              </Badge>
            ),
          },
          {
            accessor: "active",
            title: "aktif",
            sortable: true,
            render: (u) => (
              <Badge variant="light" color={u.active ? "teal" : "gray"}>
                {u.active ? "aktif" : "nonaktif"}
              </Badge>
            ),
          },
          {
            accessor: "actions",
            title: "",
            textAlign: "right",
            render: (u) => (
              <Button size="xs" variant="light" onClick={() => startEdit(u)}>
                Edit
              </Button>
            ),
          },
        ]}
      />

      <Modal opened={opened} onClose={close} title={editing ? "Edit user" : "Tambah user"}>
        <Stack>
          <TextInput label="Username" value={d.username} disabled={editing} onChange={(e) => setD({ ...d, username: e.currentTarget.value })} />
          <PasswordInput label="Password" placeholder={editing ? "(kosongkan = tak diubah)" : ""} value={d.password} onChange={(e) => setD({ ...d, password: e.currentTarget.value })} />
          <Select label="Role" data={["admin", "user"]} value={d.role} onChange={(v) => setD({ ...d, role: (v as Role) ?? "user" })} />
          {editing && <Switch label="Aktif" checked={d.active} onChange={(e) => setD({ ...d, active: e.currentTarget.checked })} />}
          <Button onClick={submit} loading={save.isPending}>
            Simpan
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
