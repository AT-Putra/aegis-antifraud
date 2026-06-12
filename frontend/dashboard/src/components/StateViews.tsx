// State views bersama: loading (skeleton, anti content-jumping), empty, error.
// Dipakai lintas halaman agar feedback ke pengguna konsisten.
import { Alert, Button, Center, Skeleton, Stack, Text, ThemeIcon } from "@mantine/core";
import { IconAlertTriangle, IconInbox, type Icon } from "@tabler/icons-react";
import type { ReactNode } from "react";

/** Skeleton baris seragam — reserve space saat data async dimuat. */
export function LoadingRows({ rows = 3, height = 56 }: { rows?: number; height?: number }) {
  return (
    <Stack gap="sm" aria-busy="true">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} height={height} radius="md" />
      ))}
    </Stack>
  );
}

/** Empty-state berikon dengan pesan & aksi opsional. */
export function EmptyState({
  label,
  hint,
  icon: Ico = IconInbox,
  action,
}: {
  label: string;
  hint?: ReactNode;
  icon?: Icon;
  action?: ReactNode;
}) {
  return (
    <Center py="xl">
      <Stack align="center" gap="xs">
        <ThemeIcon variant="light" color="gray" size={48} radius="xl">
          <Ico size={26} stroke={1.6} />
        </ThemeIcon>
        <Text fw={600}>{label}</Text>
        {hint ? (
          <Text size="sm" c="dimmed" ta="center" maw={360}>
            {hint}
          </Text>
        ) : null}
        {action}
      </Stack>
    </Center>
  );
}

/** Error-state dengan tombol coba lagi opsional. */
export function ErrorState({ label, onRetry }: { label: string; onRetry?: () => void }) {
  return (
    <Alert color="red" icon={<IconAlertTriangle size={18} />} title="Terjadi kesalahan">
      <Stack gap="xs" align="flex-start">
        <Text size="sm">{label}</Text>
        {onRetry ? (
          <Button size="xs" variant="light" color="red" onClick={onRetry}>
            Coba lagi
          </Button>
        ) : null}
      </Stack>
    </Alert>
  );
}
