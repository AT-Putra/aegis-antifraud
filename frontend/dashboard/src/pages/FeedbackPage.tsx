import { Badge, Button, Group, Stack, Table } from "@mantine/core";

import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/StateViews";
import { useFeedback, useReviewFeedback } from "../hooks/admin";

export function FeedbackPage() {
  const list = useFeedback("pending");
  const review = useReviewFeedback();

  return (
    <Stack>
      <PageHeader
        title="Review feedback"
        description="Flag dari user yang diterima menjadi label retraining model."
      />
      <Table striped data-testid="feedback-table">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>trx_id</Table.Th>
            <Table.Th>label</Table.Th>
            <Table.Th>catatan</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(list.data ?? []).map((f) => (
            <Table.Tr key={f.id}>
              <Table.Td>{f.trx_id ?? f.decision_id}</Table.Td>
              <Table.Td>
                <Badge color={f.flagged_label === "robot" ? "red" : "teal"}>{f.flagged_label}</Badge>
              </Table.Td>
              <Table.Td>{f.note}</Table.Td>
              <Table.Td>
                <Group gap="xs">
                  <Button size="xs" color="teal" onClick={() => review.mutate({ id: f.id, review_status: "accepted" })}>
                    Terima
                  </Button>
                  <Button size="xs" color="gray" variant="light" onClick={() => review.mutate({ id: f.id, review_status: "rejected" })}>
                    Tolak
                  </Button>
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      {(list.data ?? []).length === 0 && !list.isLoading && (
        <EmptyState label="Tidak ada feedback menunggu" hint="Semua flag sudah di-review." />
      )}
    </Stack>
  );
}
