"""AC-SVC (maturation): penentuan label human murni."""

from aegis.services.maturation import is_human_label


def test_human_when_matured_no_complaint() -> None:
    assert is_human_label(
        subscription_success=True, has_complaint=False, days_elapsed=10, maturation_days=7
    ) is True


def test_complaint_not_human() -> None:
    assert is_human_label(
        subscription_success=True, has_complaint=True, days_elapsed=30
    ) is False


def test_not_matured_is_none() -> None:
    assert is_human_label(
        subscription_success=True, has_complaint=False, days_elapsed=3, maturation_days=7
    ) is None


def test_no_success_is_none() -> None:
    assert is_human_label(
        subscription_success=False, has_complaint=False, days_elapsed=30
    ) is None


def test_daily_limit_reached_is_robot() -> None:
    # ADR-020: charge gagal daily_limit_reached = sinyal fraud kuat → robot.
    assert is_human_label(
        subscription_success=False, has_complaint=False, days_elapsed=30,
        charging_fail_reason="daily_limit_reached",
    ) is False


def test_insufficient_balance_still_none() -> None:
    # Gagal lain (mis. saldo kurang) bisa user asli → tetap tak pasti (None).
    assert is_human_label(
        subscription_success=False, has_complaint=False, days_elapsed=30,
        charging_fail_reason="insufficient_balance",
    ) is None
