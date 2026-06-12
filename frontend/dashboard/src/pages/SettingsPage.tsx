import { Button, Card, Group, Stack, Table, TextInput, Title } from "@mantine/core";
import { useEffect, useState } from "react";

import { usePutSetting, useSettings, useUpdateMe } from "../hooks/admin";
import { useMe } from "../hooks/queries";

export function SettingsPage() {
  const me = useMe();
  const isAdmin = me.data?.role === "admin";
  const settings = useSettings(isAdmin);
  const putSetting = usePutSetting();
  const updateMe = useUpdateMe();

  const [edits, setEdits] = useState<Record<string, string>>({});
  const [tz, setTz] = useState("");
  useEffect(() => {
    if (me.data) setTz(me.data.timezone);
  }, [me.data]);

  return (
    <Stack>
      <Title order={3}>Pengaturan</Title>

      <Card withBorder padding="md" radius="md">
        <Title order={5} mb="sm">
          Profil saya (timezone)
        </Title>
        <Group align="flex-end">
          <TextInput label="Timezone (IANA)" value={tz} onChange={(e) => setTz(e.currentTarget.value)} />
          <Button onClick={() => updateMe.mutate(tz)} loading={updateMe.isPending}>
            Simpan
          </Button>
        </Group>
      </Card>

      {isAdmin && (
        <Card withBorder padding="md" radius="md">
          <Title order={5} mb="sm">
            Pengaturan sistem
          </Title>
          <Table data-testid="settings-table">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>key</Table.Th>
                <Table.Th>value</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {(settings.data ?? []).map((s) => (
                <Table.Tr key={s.key}>
                  <Table.Td>{s.key}</Table.Td>
                  <Table.Td>
                    <TextInput
                      aria-label={s.key}
                      value={edits[s.key] ?? s.value}
                      onChange={(e) => setEdits({ ...edits, [s.key]: e.currentTarget.value })}
                    />
                  </Table.Td>
                  <Table.Td>
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => putSetting.mutate({ key: s.key, value: edits[s.key] ?? s.value })}
                    >
                      Simpan
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Stack>
  );
}
