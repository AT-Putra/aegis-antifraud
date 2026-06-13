// Tabel key-value reusable untuk menampilkan objek detail secara terbaca
// (Detail Keputusan F-11). Nilai null/undefined dirender sebagai "—".
import { Table, Text } from "@mantine/core";
import type { ReactNode } from "react";

export interface Row {
  label: string;
  value: ReactNode;
}

/** Format nilai mentah jadi tampilan ramah; null/kosong → "—".
 *  Memakai <span> (bukan <p>) agar aman disisipkan di dalam Text/Badge. */
export function fmt(v: unknown): ReactNode {
  if (v === null || v === undefined || v === "")
    return (
      <Text component="span" c="dimmed">
        —
      </Text>
    );
  if (typeof v === "boolean") return v ? "ya" : "tidak";
  if (typeof v === "number") return v.toString();
  return String(v);
}

export function KeyValue({ rows }: { rows: Row[] }) {
  return (
    <Table withRowBorders={false} verticalSpacing="xs">
      <Table.Tbody>
        {rows.map((r) => (
          <Table.Tr key={r.label}>
            <Table.Td w="40%">
              <Text size="sm" c="dimmed">
                {r.label}
              </Text>
            </Table.Td>
            <Table.Td>
              <Text component="span" size="sm">
                {r.value}
              </Text>
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}
