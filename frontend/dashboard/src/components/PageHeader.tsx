// Header halaman: judul + deskripsi singkat "halaman ini untuk apa".
// Memberi konteks ke pengguna baru tanpa mengubah alur.
import { Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  order = 3,
}: {
  title: string;
  description?: ReactNode;
  order?: 1 | 2 | 3 | 4;
}) {
  return (
    <Stack gap={2}>
      <Title order={order}>{title}</Title>
      {description ? (
        <Text size="sm" c="dimmed">
          {description}
        </Text>
      ) : null}
    </Stack>
  );
}
