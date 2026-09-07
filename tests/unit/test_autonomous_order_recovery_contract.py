import pytest

from packages.autonomy.order_recovery import OrderRecoveryPolicy, OrderRecoveryReport


def test_policy_is_immutable() -> None:
    policy = OrderRecoveryPolicy()
    with pytest.raises((AttributeError, TypeError)):
        policy.max_resubmissions = 8  # type: ignore[misc]


def test_report_is_immutable() -> None:
    report = OrderRecoveryReport(
        state="unknown",
        action="reconcile",
        reason="order_state_uncertain",
        resubmissions=0,
    )
    with pytest.raises((AttributeError, TypeError)):
        report.reason = "changed"  # type: ignore[misc]
