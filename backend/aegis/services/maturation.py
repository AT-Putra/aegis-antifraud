"""Penentuan label "human" via maturation window (TQ-06). Dipakai retraining (T-17).

Fungsi murni & deterministik. N (maturation_days) final = TQ-06 (default sementara).
"""

from __future__ import annotations

DEFAULT_MATURATION_DAYS = 7  # TQ-06 — pending tuning


def is_human_label(
    *,
    subscription_success: bool,
    has_complaint: bool,
    days_elapsed: float,
    maturation_days: int = DEFAULT_MATURATION_DAYS,
    charging_fail_reason: str | None = None,
) -> bool | None:
    """True=human, False=robot, None=belum dapat dipastikan.

    Human = langganan sukses + ter-charge + TANPA komplain setelah N hari.
    Robot = komplain, ATAU charge gagal `daily_limit_reached` (sinyal fraud kuat, ADR-020).
    Catatan: charge sukses + sinyal fraud kuat di-disqualifikasi terpisah di
    `gather_training_data` (butuh fitur trx) → bukan di sini (fungsi murni).
    """
    if has_complaint:
        return False
    if not subscription_success:
        # daily_limit_reached = sinyal fraud kuat (TRD §5) → robot; gagal lain → tak pasti.
        if charging_fail_reason == "daily_limit_reached":
            return False
        return None
    if days_elapsed < maturation_days:
        return None  # belum matang
    return True
