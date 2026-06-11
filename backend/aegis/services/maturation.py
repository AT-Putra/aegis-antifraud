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
) -> bool | None:
    """True=human, False=bukan human (komplain), None=belum dapat dipastikan.

    Human = langganan sukses + ter-charge + TANPA komplain setelah N hari.
    """
    if has_complaint:
        return False
    if not subscription_success:
        return None
    if days_elapsed < maturation_days:
        return None  # belum matang
    return True
