// Header halaman: judul + deskripsi singkat "halaman ini untuk apa" + slot aksi kanan.
// Memberi konteks ke pengguna baru tanpa mengubah alur; menyeragamkan header tiap halaman.
import { Group, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  actions,
  order = 3,
}: {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  order?: 1 | 2 | 3 | 4;
}) {
  return (
    <Group justify="space-between" align="flex-start" wrap="nowrap" mb="md">
      <Stack gap={2}>
        <Title order={order}>{title}</Title>
        {description ? (
          <Text size="sm" c="dimmed">
            {description}
          </Text>
        ) : null}
      </Stack>
      {actions ? <Group gap="sm">{actions}</Group> : null}
    </Group>
  );
}
