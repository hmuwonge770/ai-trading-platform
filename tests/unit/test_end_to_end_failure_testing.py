from packages.autonomy.end_to_end_failure_testing import (
    FailureInjection, FailureResponse, FailureType, assess_failure,
)


def test_stale_market_data_blocks_dependents():
    result = assess_failure(FailureInjection(FailureType.MARKET_DATA_STALE, "s1", "v1"))
    assert result.response is FailureResponse.BLOCK
    assert result.safe


def test_unknown_order_requires_reconciliation():
    result = assess_failure(FailureInjection(FailureType.ORDER_UNKNOWN, "s1", "v1"))
    assert result.response is FailureResponse.RECONCILE
    assert result.safe


def test_kill_switch_halts():
    result = assess_failure(FailureInjection(FailureType.KILL_SWITCH, "s1", "v1"))
    assert result.response is FailureResponse.HALT
    assert result.safe


def test_missing_identity_fails_closed():
    result = assess_failure(FailureInjection(FailureType.SECURITY_FAILURE, "", "v1"))
    assert result.response is FailureResponse.HALT
    assert not result.safe


def test_unobserved_failure_fails_closed():
    result = assess_failure(FailureInjection(FailureType.EXCHANGE_DISCONNECT, "s1", "v1", False))
    assert result.response is FailureResponse.HALT
    assert not result.safe


def test_assessment_is_deterministic():
    injection = FailureInjection(FailureType.RECONCILIATION_MISMATCH, "s1", "v1")
    assert assess_failure(injection) == assess_failure(injection)
