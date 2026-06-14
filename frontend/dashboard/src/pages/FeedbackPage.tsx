import { Badge, Button, Group, Stack, Text } from "@mantine/core";
import { DataTable } from "mantine-datatable";

import type { FeedbackItem } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { QuickFilter } from "../components/QuickFilter";
import { useClientTable } from "../lib/clientTable";
import { useFeedback, useReviewFeedback } from "../hooks/admin";

export function FeedbackPage() {
  const list = useFeedback("pending");
  const review = useReviewFeedback();

  const t = useClientTable<FeedbackItem>(list.data ?? [], {
    initialSort: { columnAccessor: "trx_id", direction: "asc" },
    filterKeys: ["trx_id", "flagged_label", "note"],
  });

  return (
    <Stack>
      <PageHeader
        title="Review feedback"
        description="Flag dari user yang diterima menjadi label retraining model."
      />
      <Group justify="flex-end">
        <QuickFilter value={t.query} onChange={t.setQuery} placeholder="Filter feedback…" testid="feedback-filter" />
      </Group>
      <DataTable<FeedbackItem>
        data-testid="feedback-table"
        minHeight={180}
        withTableBorder
        borderRadius="md"
        striped
        highlightOnHover
        records={t.paged}
        idAccessor="id"
        fetching={list.isLoading}
        noRecordsText="Tidak ada feedback menunggu"
        page={t.page}
        onPageChange={t.setPage}
        totalRecords={t.total}
        recordsPerPage={t.pageSize}
        sortStatus={t.sort}
        onSortStatusChange={t.setSort}
        columns={[
          {
            accessor: "trx_id",
            sortable: true,
            render: (f) => f.trx_id ?? f.decision_id ?? "—",
          },
          {
            accessor: "flagged_label",
            title: "label",
            sortable: true,
            render: (f) => (
              <Badge color={f.flagged_label === "robot" ? "red" : "teal"}>{f.flagged_label}</Badge>
            ),
          },
          {
            accessor: "note",
            title: "catatan",
            render: (f) => f.note ?? <Text c="dimmed" size="sm">—</Text>,
          },
          {
            accessor: "actions",
            title: "",
            textAlign: "right",
            render: (f) => (
              <Group gap="xs" justify="flex-end" wrap="nowrap">
                <Button size="xs" color="teal" onClick={() => review.mutate({ id: f.id, review_status: "accepted" })}>
                  Terima
                </Button>
                <Button size="xs" color="gray" variant="light" onClick={() => review.mutate({ id: f.id, review_status: "rejected" })}>
                  Tolak
                </Button>
              </Group>
            ),
          },
        ]}
      />
    </Stack>
  );
}
