import type { DataTableSortStatus } from "mantine-datatable";
import { useMemo, useState } from "react";

// Ukuran halaman standar tabel admin (data bervolume kecil → semua client-side).
export const ADMIN_PAGE_SIZE = 10;

interface Options<T> {
  initialSort: DataTableSortStatus<T>;
  /** Kolom yang dicocokkan oleh quick filter teks (substring, case-insensitive). */
  filterKeys?: (keyof T)[];
  pageSize?: number;
}

/**
 * State tabel admin sisi-klien: quick filter + sort kolom + pagination.
 * Selaras pola DashboardPage/SearchPage (sort & paginate di klien karena data admin kecil).
 */
export function useClientTable<T>(rows: T[], opts: Options<T>) {
  const { initialSort, filterKeys, pageSize = ADMIN_PAGE_SIZE } = opts;
  const [query, setQueryRaw] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<DataTableSortStatus<T>>(initialSort);

  const setQuery = (v: string) => {
    setQueryRaw(v);
    setPage(1); // hasil filter berubah → kembali ke halaman pertama
  };

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q || !filterKeys?.length) return rows;
    return rows.filter((r) =>
      filterKeys.some((k) => {
        const v = r[k];
        return v != null && String(v).toLowerCase().includes(q);
      }),
    );
  }, [rows, query, filterKeys]);

  const sorted = useMemo(() => {
    const key = sort.columnAccessor as keyof T;
    const copy = [...filtered];
    copy.sort((a, b) => {
      const av = a[key] ?? "";
      const bv = b[key] ?? "";
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sort.direction === "desc" ? -cmp : cmp;
    });
    return copy;
  }, [filtered, sort]);

  // Clamp halaman bila di luar jangkauan (mis. setelah data menyusut).
  const safePage = Math.min(page, Math.max(1, Math.ceil(sorted.length / pageSize)));
  const paged = sorted.slice((safePage - 1) * pageSize, safePage * pageSize);

  return {
    query,
    setQuery,
    page: safePage,
    setPage,
    sort,
    setSort,
    paged,
    total: sorted.length,
    pageSize,
  };
}
