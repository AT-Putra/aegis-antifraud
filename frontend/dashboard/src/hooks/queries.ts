// Hook data (TanStack Query) untuk endpoint analytics & profil (03 §6/§7).
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
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

const f = (x: AnalyticsFilters): Record<string, unknown> => ({
  from: x.from,
  to: x.to,
  tz: x.tz,
  service: x.service,
  campaign: x.campaign,
  source: x.source,
  pub_id: x.pub_id,
});

export const useMe = () => useQuery({ queryKey: ["me"], queryFn: () => api.get<Me>("/v1/users/me") });

export const useSummary = (filters: AnalyticsFilters) =>
  useQuery({
    queryKey: ["summary", filters],
    queryFn: () => api.get<Summary>("/v1/analytics/summary", f(filters)),
  });

export const useTimeseries = (metric: string, granularity: string, filters: AnalyticsFilters) =>
  useQuery({
    queryKey: ["timeseries", metric, granularity, filters],
    queryFn: () =>
      api.get<TimeseriesPoint[]>("/v1/analytics/timeseries", { metric, granularity, ...f(filters) }),
  });

export const useBreakdown = (dimension: string, filters: AnalyticsFilters) =>
  useQuery({
    queryKey: ["breakdown", dimension, filters],
    queryFn: () => api.get<BreakdownItem[]>("/v1/analytics/breakdown", { dimension, ...f(filters) }),
  });

export const useBlockReasons = (filters: AnalyticsFilters, limit = 10) =>
  useQuery({
    queryKey: ["block-reasons", filters, limit],
    queryFn: () => api.get<BlockReasonItem[]>("/v1/analytics/block-reasons", { ...f(filters), limit }),
  });

export const useBehaviorStats = (filters: AnalyticsFilters) =>
  useQuery({
    queryKey: ["behavior-stats", filters],
    queryFn: () => api.get<BehaviorStatItem[]>("/v1/analytics/behavior-stats", f(filters)),
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
