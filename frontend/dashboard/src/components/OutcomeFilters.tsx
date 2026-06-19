// Filter outcome langganan BERJENJANG (T-27), gaya chained seperti service→campaign:
//   L1 "Langganan" (sukses berlangganan) → bila dipilih, muncul
//   L2 "Status charging" (sukses/gagal)  → bila gagal, muncul
//   L3 "Alasan gagal" (pulsa tidak cukup / limit harian / lainnya)
// Default semua = kosong = tampilkan semua. Kode reason kanonik = schemas/callback.py.
import { Select } from "@mantine/core";

export interface OutcomeFilterValue {
  subscribed: string; // "" | "true"
  charging_status: string; // "" | "success" | "failed"
  charging_fail_reason: string; // "" | insufficient_balance | daily_limit_reached | other
}

const FAIL_REASONS = [
  { value: "insufficient_balance", label: "Pulsa tidak cukup" },
  { value: "daily_limit_reached", label: "Limit charging harian" },
  { value: "other", label: "Kegagalan lainnya" },
];

export function OutcomeFilters({
  value,
  onChange,
  width = 200,
}: {
  value: OutcomeFilterValue;
  onChange: (next: OutcomeFilterValue) => void;
  width?: number | string;
}) {
  const showCharging = value.subscribed === "true";
  const showReason = showCharging && value.charging_status === "failed";

  return (
    <>
      <Select
        label="Langganan"
        aria-label="Langganan"
        placeholder="semua"
        data={[{ value: "true", label: "Sukses berlangganan" }]}
        value={value.subscribed || null}
        // clear L1 → reset seluruh cabang di bawahnya
        onChange={(v) =>
          onChange(
            v
              ? { ...value, subscribed: "true" }
              : { subscribed: "", charging_status: "", charging_fail_reason: "" },
          )
        }
        clearable
        w={width}
      />
      {showCharging && (
        <Select
          label="Status charging"
          aria-label="Status charging"
          placeholder="semua"
          data={[
            { value: "success", label: "Sukses" },
            { value: "failed", label: "Gagal" },
          ]}
          value={value.charging_status || null}
          // ganti dari 'gagal' → reset alasan gagal (L3 tak relevan lagi)
          onChange={(v) =>
            onChange({ ...value, charging_status: v ?? "", charging_fail_reason: "" })
          }
          clearable
          w={width}
        />
      )}
      {showReason && (
        <Select
          label="Alasan gagal"
          aria-label="Alasan gagal"
          placeholder="semua"
          data={FAIL_REASONS}
          value={value.charging_fail_reason || null}
          onChange={(v) => onChange({ ...value, charging_fail_reason: v ?? "" })}
          clearable
          w={width}
        />
      )}
    </>
  );
}
