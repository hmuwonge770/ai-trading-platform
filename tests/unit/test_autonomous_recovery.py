from packages.autonomy.recovery import (
    AutonomousRecoveryEngine,
    RecoveryAction,
    RecoveryEvent,
    RecoveryPolicy,
)


def test_success_resets_recovery_state() -> None:
    engine = AutonomousRecoveryEngine()
    engine.observe(RecoveryEvent.EXECUTION_ERROR)
    result = engine.observe(RecoveryEvent.SUCCESS)
    assert result.action is RecoveryAction.CONTINUE
    assert engine.state.consecutive_failures == 0
    assert engine.state.retries == 0


def test_transient_execution_errors_are_bounded() -> None:
    engine = AutonomousRecoveryEngine(RecoveryPolicy(max_consecutive_failures=4, max_retries=2))
    first = engine.observe(RecoveryEvent.EXECUTION_ERROR)
    second = engine.observe(RecoveryEvent.EXECUTION_ERROR)
    third = engine.observe(RecoveryEvent.EXECUTION_ERROR)
    assert first.action is RecoveryAction.RETRY
    assert second.action is RecoveryAction.RETRY
    assert third.action is RecoveryAction.HALT
    assert third.reason == "retry_budget_exhausted"


def test_unknown_failure_halts_immediately() -> None:
    result = AutonomousRecoveryEngine().observe(RecoveryEvent.UNKNOWN_FAILURE)
    assert result.action is RecoveryAction.HALT
    assert result.reason == "unknown_failure"


def test_reconciliation_mismatch_halts() -> None:
    result = AutonomousRecoveryEngine().observe(RecoveryEvent.RECONCILIATION_MISMATCH)
    assert result.action is RecoveryAction.HALT
    assert result.reason == "reconciliation_mismatch"


def test_stale_market_data_halts() -> None:
    result = AutonomousRecoveryEngine().observe(
        RecoveryEvent.MARKET_STALE,
        market_age_seconds=31,
    )
    assert result.action is RecoveryAction.HALT
    assert result.reason == "market_data_stale"


def test_unknown_market_age_fails_closed() -> None:
    result = AutonomousRecoveryEngine().observe(RecoveryEvent.MARKET_STALE)
    assert result.action is RecoveryAction.HALT
    assert result.reason == "market_age_unknown"


def test_halt_requires_reconciliation_before_reset() -> None:
    engine = AutonomousRecoveryEngine()
    engine.observe(RecoveryEvent.RECONCILIATION_MISMATCH)
    blocked = engine.observe(RecoveryEvent.SUCCESS)
    assert blocked.action is RecoveryAction.HALT
    reset = engine.reset_after_reconciliation()
    assert reset.action is RecoveryAction.CONTINUE
    assert reset.reason == "reconciled_and_reset"


def test_invalid_policy_is_rejected() -> None:
    try:
        RecoveryPolicy(max_retries=-1)
    except ValueError as exc:
        assert "max_retries" in str(exc)
    else:
        raise AssertionError("invalid policy was accepted")
