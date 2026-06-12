import { Badge, Button, Modal, PasswordInput, Select, Stack, Switch, Table, TextInput } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconPlus } from "@tabler/icons-react";
import { useState } from "react";

import type { Role, UserOut } from "../api/types";
import { PageHeader } from "../components/PageHeader";
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
      <Table striped highlightOnHover data-testid="users-table">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>username</Table.Th>
            <Table.Th>role</Table.Th>
            <Table.Th>aktif</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(list.data ?? []).map((u) => (
            <Table.Tr key={u.id}>
              <Table.Td>{u.username}</Table.Td>
              <Table.Td>
                <Badge variant="light" color={u.role === "admin" ? "indigo" : "gray"}>
                  {u.role}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Badge variant="light" color={u.active ? "teal" : "gray"}>
                  {u.active ? "aktif" : "nonaktif"}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Button size="xs" variant="light" onClick={() => startEdit(u)}>
                  Edit
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>

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
