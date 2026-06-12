import { Badge, Button, Group, Stack, Table, Text, Title } from "@mantine/core";

import { useFeedback, useReviewFeedback } from "../hooks/admin";

export function FeedbackPage() {
  const list = useFeedback("pending");
  const review = useReviewFeedback();

  return (
    <Stack>
      <Title order={3}>Review feedback</Title>
      <Text c="dimmed" size="sm">
        Flag yang diterima menjadi label retraining.
      </Text>
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
    </Stack>
  );
}
