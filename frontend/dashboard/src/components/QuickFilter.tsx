// Kotak filter teks cepat untuk tabel admin (filter client-side, substring).
import { CloseButton, TextInput } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";

export function QuickFilter({
  value,
  onChange,
  placeholder = "Filter…",
  testid,
  width = 240,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  testid?: string;
  width?: number;
}) {
  return (
    <TextInput
      data-testid={testid}
      aria-label={placeholder}
      placeholder={placeholder}
      value={value}
      onChange={(e) => onChange(e.currentTarget.value)}
      leftSection={<IconSearch size={15} stroke={1.8} />}
      rightSection={
        value ? (
          <CloseButton size="sm" aria-label="Bersihkan filter" onClick={() => onChange("")} />
        ) : null
      }
      w={width}
    />
  );
}
