import type { DataTableSortStatus } from "mantine-datatable";
import { useMemo, useState } from "react";

// Ukuran halaman standar tabel admin (data bervolume kecil → semua client-side).
export const ADMIN_PAGE_SIZE = 10;

/**
 * Bandingkan dua nilai sel untuk sort, arah ascending.
 * - null/undefined **selalu** di akhir (lepas dari arah sort — penanganan di pemanggil).
 * - dua angka dibanding numerik (hindari coercion `0 < ""` yang membuat null≈0).
 * - selain itu leksikal (string, case-sensitive sesuai data).
 * Return >0 berarti `a` setelah `b`; dipakai dgn flag `nullsLast` agar null tak ikut dibalik desc.
 */
export function compareValues(av: unknown, bv: unknown): { cmp: number; bothNull: boolean } {
  const aNull = av == null;
  const bNull = bv == null;
  if (aNull && bNull) return { cmp: 0, bothNull: true };
  if (aNull) return { cmp: 1, bothNull: false }; // a kosong → setelah b
  if (bNull) return { cmp: -1, bothNull: false };
  if (typeof av === "number" && typeof bv === "number") {
    return { cmp: av - bv, bothNull: false };
  }
  const as = String(av);
  const bs = String(bv);
  return { cmp: as < bs ? -1 : as > bs ? 1 : 0, bothNull: false };
}

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
    const desc = sort.direction === "desc";
    copy.sort((a, b) => {
      const { cmp, bothNull } = compareValues(a[key], b[key]);
      if (bothNull) return 0;
      // Salah satu null → selalu di akhir; jangan ikut dibalik oleh desc.
      if (a[key] == null || b[key] == null) return cmp;
      return desc ? -cmp : cmp;
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
