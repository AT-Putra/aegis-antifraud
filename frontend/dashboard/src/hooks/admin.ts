// Hook admin (03 §6): queries + mutations dengan invalidasi + notifikasi.
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, api } from "../api/client";
import type {
  CampaignOut,
  ConfigOut,
  ConfigVersionItem,
  FeedbackItem,
  ModelOut,
  ServiceOut,
  SettingItem,
  UserOut,
} from "../api/types";

function notifyError(e: unknown): void {
  const msg = e instanceof ApiError ? e.message : "Terjadi kesalahan.";
  notifications.show({ color: "red", message: msg });
}
function notifyOk(message: string): void {
  notifications.show({ color: "teal", message });
}

function useInvalidate(keys: string[]) {
  const qc = useQueryClient();
  return () => keys.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
}

// --- Config ---
export const useConfig = () =>
  useQuery({ queryKey: ["config"], queryFn: () => api.get<ConfigOut>("/v1/admin/config") });
export const useConfigVersions = () =>
  useQuery({
    queryKey: ["config-versions"],
    queryFn: () => api.get<ConfigVersionItem[]>("/v1/admin/config/versions"),
  });
export const fetchConfigVersion = (v: number) => api.get<ConfigOut>(`/v1/admin/config/${v}`);

export function usePutConfig() {
  const inv = useInvalidate(["config", "config-versions"]);
  return useMutation({
    mutationFn: (body: { params: unknown; threshold: number; blend_weights: unknown }) =>
      api.put<{ version: number }>("/v1/admin/config", body),
    onSuccess: (r) => {
      inv();
      notifyOk(`Config versi ${r.version} aktif.`);
    },
    onError: notifyError,
  });
}

// --- Settings ---
export const useSettings = (enabled = true) =>
  useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get<SettingItem[]>("/v1/admin/settings"),
    enabled,
  });
export function usePutSetting() {
  const inv = useInvalidate(["settings"]);
  return useMutation({
    mutationFn: (b: SettingItem) => api.put<SettingItem>("/v1/admin/settings", b),
    onSuccess: () => {
      inv();
      notifyOk("Pengaturan disimpan.");
    },
    onError: notifyError,
  });
}

// --- Services ---
export const useServices = () =>
  useQuery({ queryKey: ["services"], queryFn: () => api.get<ServiceOut[]>("/v1/admin/services") });
export function useSaveService() {
  const inv = useInvalidate(["services"]);
  return useMutation({
    mutationFn: (v: { id?: string; body: Record<string, unknown> }) =>
      v.id ? api.put(`/v1/admin/services/${v.id}`, v.body) : api.post("/v1/admin/services", v.body),
    onSuccess: () => {
      inv();
      notifyOk("Layanan disimpan.");
    },
    onError: notifyError,
  });
}

// --- Campaigns ---
export const useCampaigns = () =>
  useQuery({ queryKey: ["campaigns"], queryFn: () => api.get<CampaignOut[]>("/v1/admin/campaigns") });
export function useSaveCampaign() {
  const inv = useInvalidate(["campaigns"]);
  return useMutation({
    mutationFn: (v: { id?: string; body: Record<string, unknown> }) =>
      v.id ? api.put(`/v1/admin/campaigns/${v.id}`, v.body) : api.post("/v1/admin/campaigns", v.body),
    onSuccess: () => {
      inv();
      notifyOk("Campaign disimpan.");
    },
    onError: notifyError,
  });
}

// --- Users ---
export const useUsers = () =>
  useQuery({ queryKey: ["users"], queryFn: () => api.get<UserOut[]>("/v1/admin/users") });
export function useSaveUser() {
  const inv = useInvalidate(["users"]);
  return useMutation({
    mutationFn: (v: { id?: string; body: Record<string, unknown> }) =>
      v.id ? api.put(`/v1/admin/users/${v.id}`, v.body) : api.post("/v1/admin/users", v.body),
    onSuccess: () => {
      inv();
      notifyOk("User disimpan.");
    },
    onError: notifyError,
  });
}

// --- Feedback ---
export const useFeedback = (status = "pending") =>
  useQuery({
    queryKey: ["feedback", status],
    queryFn: () => api.get<FeedbackItem[]>("/v1/admin/feedback", { status }),
  });
export function useReviewFeedback() {
  const inv = useInvalidate(["feedback"]);
  return useMutation({
    mutationFn: (v: { id: string; review_status: "accepted" | "rejected" }) =>
      api.put(`/v1/admin/feedback/${v.id}/review`, { review_status: v.review_status }),
    onSuccess: () => {
      inv();
      notifyOk("Feedback diproses.");
    },
    onError: notifyError,
  });
}
export function useSubmitFeedback() {
  return useMutation({
    mutationFn: (b: { trx_id: string; flagged_label: "human" | "robot"; note?: string }) =>
      api.post("/v1/feedback", b),
    onSuccess: () => notifyOk("Flag terkirim."),
    onError: notifyError,
  });
}

// --- Models / retraining ---
export const useModels = () =>
  useQuery({ queryKey: ["models"], queryFn: () => api.get<ModelOut[]>("/v1/admin/models") });
export function useActivateModel() {
  const inv = useInvalidate(["models"]);
  return useMutation({
    mutationFn: (id: string) => api.post(`/v1/admin/models/${id}/activate`),
    onSuccess: () => {
      inv();
      notifyOk("Model diaktifkan (efektif setelah restart API).");
    },
    onError: notifyError,
  });
}
export function useRetrain() {
  return useMutation({
    mutationFn: () => api.post<{ job_id: string; status: string }>("/v1/admin/retrain"),
    onSuccess: (r) => notifyOk(`Job retrain ${r.job_id} (${r.status}).`),
    onError: notifyError,
  });
}

// --- Profil ---
export function useUpdateMe() {
  const inv = useInvalidate(["me"]);
  return useMutation({
    mutationFn: (timezone: string) => api.put("/v1/users/me", { timezone }),
    onSuccess: () => {
      inv();
      notifyOk("Timezone diperbarui.");
    },
    onError: notifyError,
  });
}
