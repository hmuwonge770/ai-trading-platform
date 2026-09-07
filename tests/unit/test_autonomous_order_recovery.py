import pytest

from packages.autonomy.order_recovery import (
    AutonomousOrderLifecycleRecovery,
    OrderLifecycleState,
    OrderRecoveryAction,
    OrderRecoveryEvent,
    OrderRecoveryPolicy,
)


def test_response_loss_requires_reconciliation() -> None:
    recovery = AutonomousOrderLifecycleRecovery(client_order_id="client-1")

    report = recovery.observe(OrderRecoveryEvent.RESPONSE_LOST)

    assert report.state is OrderLifecycleState.UNKNOWN
    assert report.action is OrderRecoveryAction.RECONCILE


def test_confirmed_absence_allows_one_bounded_resubmission() -> None:
    recovery = AutonomousOrderLifecycleRecovery(client_order_id="client-2")
    recovery.observe(OrderRecoveryEvent.RESPONSE_LOST)

    report = recovery.observe(OrderRecoveryEvent.CONFIRMED_NOT_FOUND)

    assert report.action is OrderRecoveryAction.RETRY_SUBMISSION
    assert report.state is OrderLifecycleState.SUBMITTED
    assert report.resubmissions == 1


def test_resubmission_budget_is_fail_closed() -> None:
    recovery = AutonomousOrderLifecycleRecovery(
        client_order_id="client-3",
        policy=OrderRecoveryPolicy(max_resubmissions=1),
    )
    recovery.observe(OrderRecoveryEvent.RESPONSE_LOST)
    recovery.observe(OrderRecoveryEvent.CONFIRMED_NOT_FOUND)
    recovery.observe(OrderRecoveryEvent.RESPONSE_LOST)

    report = recovery.observe(OrderRecoveryEvent.CONFIRMED_NOT_FOUND)

    assert report.action is OrderRecoveryAction.HALT
    assert report.reason == "resubmission_budget_exhausted"


def test_query_failure_never_directly_retries() -> None:
    recovery = AutonomousOrderLifecycleRecovery(client_order_id="client-4")

    report = recovery.observe(OrderRecoveryEvent.QUERY_FAILED)

    assert report.state is OrderLifecycleState.UNKNOWN
    assert report.action is OrderRecoveryAction.RECONCILE
    assert report.resubmissions == 0


def test_terminal_state_is_stable() -> None:
    recovery = AutonomousOrderLifecycleRecovery(client_order_id="client-5")
    recovery.observe(OrderRecoveryEvent.FILLED)

    report = recovery.observe(OrderRecoveryEvent.RESPONSE_LOST)

    assert report.state is OrderLifecycleState.FILLED
    assert report.action is OrderRecoveryAction.CONTINUE
    assert report.reason == "terminal_order_state"


def test_normal_partial_fill_then_fill() -> None:
    recovery = AutonomousOrderLifecycleRecovery(client_order_id="client-6")

    partial = recovery.observe(OrderRecoveryEvent.PARTIAL_FILL)
    filled = recovery.observe(OrderRecoveryEvent.FILLED)

    assert partial.state is OrderLifecycleState.PARTIALLY_FILLED
    assert filled.state is OrderLifecycleState.FILLED


def test_not_found_without_uncertain_state_halts() -> None:
    recovery = AutonomousOrderLifecycleRecovery(client_order_id="client-7")

    report = recovery.observe(OrderRecoveryEvent.CONFIRMED_NOT_FOUND)

    assert report.action is OrderRecoveryAction.HALT
    assert report.reason == "not_found_without_uncertainty"


def test_empty_client_order_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="client_order_id"):
        AutonomousOrderLifecycleRecovery(client_order_id=" ")


def test_negative_resubmission_budget_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_resubmissions"):
        OrderRecoveryPolicy(max_resubmissions=-1)
