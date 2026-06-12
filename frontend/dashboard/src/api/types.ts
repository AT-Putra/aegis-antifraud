// Tipe kontrak (03 §6/§7) yang dikonsumsi dashboard.

export type Role = "admin" | "user";

export interface Me {
  id: string;
  username: string;
  role: Role;
  timezone: string;
}

export interface Summary {
  total: number;
  allow: number;
  block: number;
  weboptin_failed: number;
  fraud_est: number;
  complaints: number;
  charging_fail_breakdown: Record<string, number>;
}

export interface TimeseriesPoint {
  bucket_ts: string;
  value: number;
}

export interface BreakdownItem {
  key: string;
  count: number;
}

export interface SearchResultItem {
  trx_id: string;
  device_id: string | null;
  service: string | null;
  campaign: string | null;
  source: string | null;
  pub_id: string | null;
  decision: string;
  weboptin_status: string | null;
  final_score: number | null;
  ts: string;
}

export interface DecisionDetail {
  trx_id: string;
  device_id: string | null;
  service: string | null;
  campaign: string | null;
  source: string | null;
  pub_id: string | null;
  decision: string;
  weboptin_status: string | null;
  weboptin_host: string | null;
  final_score: number | null;
  score_breakdown: Record<string, unknown>;
  signals: Record<string, unknown>;
  ip_intelligence: Record<string, unknown>;
  device_info: Record<string, unknown>;
  rules_version: number | null;
  model_version: number | null;
  outcome: Record<string, unknown> | null;
}

export interface AnalyticsFilters {
  from?: string | null;
  to?: string | null;
  tz?: string;
  service?: string | null;
  campaign?: string | null;
  source?: string | null;
  pub_id?: string | null;
}
