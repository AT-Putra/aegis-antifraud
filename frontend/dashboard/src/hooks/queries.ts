// Hook data (TanStack Query) untuk endpoint analytics & profil (03 §6/§7).
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import { startOfTodayUtcIso, wallToUtcIso } from "../lib/tz";
import type {
  AnalyticsFilters,
  BehaviorStatItem,
  BlockReasonItem,
  BreakdownItem,
  DecisionDetail,
  Me,
  RegistryOption,
  SearchResultItem,
  Summary,
  TimeseriesPoint,
} from "../api/types";

// ADR-017: default tanpa filter waktu = HARI INI 00:00→sekarang dalam timezone pengaturan.
// from/to yang diisi pengguna = wall-time tz → dikonversi ke instant UTC sebelum dikirim
// (kontrak API tetap menerima UTC). to kosong → diabaikan (backend pakai now).
const f = (x: AnalyticsFilters): Record<string, unknown> => {
  const tz = x.tz || "Asia/Jakarta";
  return {
    from: x.from ? wallToUtcIso(x.from, tz) : startOfTodayUtcIso(tz),
    to: x.to ? wallToUtcIso(x.to, tz) : undefined,
    tz,
    service: x.service,
    campaign: x.campaign,
    source: x.source,
    pub_id: x.pub_id,
  };
};

// Polling realtime komponen analytics non-feed (KPI/chart/breakdown/stats).
// Hanya saat rentang "live": `to` kosong = data sampai sekarang → terus berubah.
// Rentang historis tertutup (`to` terisi) = statis → tak perlu poll (hemat OLAP).
const LIVE_REFETCH_MS = 20_000;
const liveInterval = (x: AnalyticsFilters): number | false => (x.to ? false : LIVE_REFETCH_MS);

export const useMe = () => useQuery({ queryKey: ["me"], queryFn: () => api.get<Me>("/v1/users/me") });

export const useSummary = (filters: AnalyticsFilters) =>
  useQuery({
    queryKey: ["summary", filters],
    queryFn: () => api.get<Summary>("/v1/analytics/summary", f(filters)),
    refetchInterval: liveInterval(filters),
  });

export const useTimeseries = (metric: string, granularity: string, filters: AnalyticsFilters) =>
  useQuery({
    queryKey: ["timeseries", metric, granularity, filters],
    queryFn: () =>
      api.get<TimeseriesPoint[]>("/v1/analytics/timeseries", { metric, granularity, ...f(filters) }),
    refetchInterval: liveInterval(filters),
  });

export const useBreakdown = (dimension: string, filters: AnalyticsFilters) =>
  useQuery({
    queryKey: ["breakdown", dimension, filters],
    queryFn: () => api.get<BreakdownItem[]>("/v1/analytics/breakdown", { dimension, ...f(filters) }),
    refetchInterval: liveInterval(filters),
  });

export const useBlockReasons = (filters: AnalyticsFilters, limit = 10) =>
  useQuery({
    queryKey: ["block-reasons", filters, limit],
    queryFn: () => api.get<BlockReasonItem[]>("/v1/analytics/block-reasons", { ...f(filters), limit }),
    refetchInterval: liveInterval(filters),
  });

export const useBehaviorStats = (filters: AnalyticsFilters) =>
  useQuery({
    queryKey: ["behavior-stats", filters],
    queryFn: () => api.get<BehaviorStatItem[]>("/v1/analytics/behavior-stats", f(filters)),
    refetchInterval: liveInterval(filters),
  });

export const useSearch = (params: Record<string, unknown>, enabled: boolean) =>
  useQuery({
    queryKey: ["search", params],
    queryFn: () => api.get<SearchResultItem[]>("/v1/analytics/search", params),
    enabled,
  });

export const useDecision = (trxId: string) =>
  useQuery({
    queryKey: ["decision", trxId],
    queryFn: () => api.get<DecisionDetail>(`/v1/analytics/decision/${encodeURIComponent(trxId)}`),
    enabled: !!trxId,
  });

// Opsi dropdown filter (registry read-only). Campaign chained: ikut service terpilih.
export const useServiceOptions = () =>
  useQuery({
    queryKey: ["registry-services"],
    queryFn: () => api.get<RegistryOption[]>("/v1/registry/services"),
    staleTime: 5 * 60_000,
  });

export const useCampaignOptions = (service?: string | null) =>
  useQuery({
    queryKey: ["registry-campaigns", service ?? null],
    queryFn: () => api.get<RegistryOption[]>("/v1/registry/campaigns", { service }),
    enabled: !!service,
    staleTime: 5 * 60_000,
  });

// Opsi negara untuk dropdown filter Pencarian (distinct dari OLAP; T-27).
export const useCountryOptions = () =>
  useQuery({
    queryKey: ["analytics-countries"],
    queryFn: () => api.get<string[]>("/v1/analytics/countries"),
    staleTime: 5 * 60_000,
  });
