// Stub untuk layar manajemen yang dibangun di 16b (config/services/campaigns/users/settings/feedback).
import { Alert, Title, Stack } from "@mantine/core";

export function PlaceholderPage({ title }: { title: string }) {
  return (
    <Stack>
      <Title order={3}>{title}</Title>
      <Alert color="blue" variant="light">
        Layar ini akan dibangun di T-16b.
      </Alert>
    </Stack>
  );
}
