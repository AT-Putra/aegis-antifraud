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

// Funnel langganan & charging (T-30): agregat outcome OLAP utk panel in-depth Analitik.
export interface ChargingFunnel {
  registration_success: number; // callback subscription = registrasi/langganan sukses
  charging_success: number;
  charging_failed: number;
  charging_fail_breakdown: Record<string, number>; // insufficient_balance|daily_limit_reached|other
  complaints: number;
}

export interface TimeseriesPoint {
  bucket_ts: string;
  value: number;
}

export interface BreakdownItem {
  key: string;
  count: number;
}

// Opsi dropdown filter service/campaign (registry read-only, 03 §7).
export interface RegistryOption {
  slug: string;
  name: string;
  status: string;
}

// Statistik analitik tambahan (03 §7).
export interface BlockReasonItem {
  reason: string;
  count: number;
}
export interface BehaviorStatItem {
  metric: string;
  label: string;
  avg: number;
  sample: number;
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

// Penjelasan audit-grade keputusan (03 §7). Opsional: absen/available:false utk baris lama.
export interface RuleFactor {
  name: string;
  label: string;
  value: number;
  weight: number;
  contribution: number;
}
export interface BlendComponent {
  name: string;
  label: string;
  score: number | null;
  weight: number;
  normalized_weight: number;
  contribution: number;
  applied: boolean;
}
export interface Explainability {
  available: boolean;
  version?: string;
  feature_source?: string;
  warnings?: string[];
  rules_version_used?: number | null;
  rules?: {
    formula: string;
    applied_mode: string;
    soft_sum: number;
    soft_score: number;
    effective_score: number;
    hard_rules_enabled: string[];
    hard_rules_triggered: string[];
    factors: RuleFactor[];
  };
  blend?: {
    final_score: number | null;
    threshold: number;
    decision: string;
    reason: string | null;
    mode: string;
    components: BlendComponent[];
  };
  models?: { attribution_available: boolean; note: string };
  rationale?: string;
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
  explainability?: Explainability | null;
}

// --- Admin (03 §6) ---
export interface ConfigOut {
  version: number;
  params: Record<string, unknown>;
  threshold: number;
  blend_weights: Record<string, unknown>;
  guidelines?: Record<string, unknown> | null;
  active?: boolean;
}
export interface ConfigVersionItem {
  version: number;
  created_by: string | null;
  created_at: string;
  active: boolean;
}
export interface SettingItem {
  key: string;
  value: string;
}
export interface ServiceOut {
  id: string;
  slug: string;
  name: string;
  operator: string | null;
  cp_api_url: string;
  status: "active" | "inactive";
  created_at: string;
  updated_at: string;
}
export interface CampaignOut {
  id: string;
  slug: string;
  name: string;
  service: string;
  allowed_origins: string[];
  allowed_countries: string[]; // ISO 3166-1 alpha-2; [] = ALL (tanpa batas geo). F-17
  home_country: string | null; // ISO 3166-1 alpha-2; null = tanpa ekspektasi geo. ADR-020
  expect_mobile_carrier: boolean; // harap IP operator seluler (mis. billing Telkomsel). ADR-020
  status: "active" | "inactive";
  created_at: string;
  updated_at: string;
}
export interface UserOut {
  id: string;
  username: string;
  role: Role;
  active: boolean;
}
export interface ModelOut {
  id: string;
  version: number;
  algorithm: string;
  trained_at: string | null;
  metrics: Record<string, unknown>;
  active: boolean;
}
export interface RetrainJob {
  job_id: string;
  status: string;
  metrics?: Record<string, unknown> | null;
}
export interface FeedbackItem {
  id: string;
  trx_id: string | null;
  decision_id: string | null;
  flagged_label: string;
  note: string | null;
  review_status: string;
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
