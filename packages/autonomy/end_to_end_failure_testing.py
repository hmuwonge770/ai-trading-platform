"""Deterministic end-to-end failure injection and safety assessment."""
from dataclasses import dataclass
from enum import StrEnum


class FailureType(StrEnum):
    MARKET_DATA_STALE = "market_data_stale"
    DECISION_STALE = "decision_stale"
    RISK_REJECTION = "risk_rejection"
    AUTHORIZATION_FAILURE = "authorization_failure"
    EXCHANGE_DISCONNECT = "exchange_disconnect"
    ORDER_UNKNOWN = "order_unknown"
    RECONCILIATION_MISMATCH = "reconciliation_mismatch"
    POSITION_MISMATCH = "position_mismatch"
    ACCOUNTING_MISMATCH = "accounting_mismatch"
    KILL_SWITCH = "kill_switch"
    STATE_CORRUPTION = "state_corruption"
    SECURITY_FAILURE = "security_failure"


class FailureResponse(StrEnum):
    HALT = "halt"
    BLOCK = "block"
    RECONCILE = "reconcile"
    RECOVER = "recover"


@dataclass(frozen=True, slots=True)
class FailureInjection:
    failure: FailureType
    strategy_id: str
    strategy_version: str
    observed: bool = True


@dataclass(frozen=True, slots=True)
class FailureAssessment:
    failure: FailureType
    response: FailureResponse
    safe: bool
    reasons: tuple[str, ...]


_CRITICAL = frozenset({
    FailureType.MARKET_DATA_STALE, FailureType.DECISION_STALE,
    FailureType.RISK_REJECTION, FailureType.AUTHORIZATION_FAILURE,
    FailureType.EXCHANGE_DISCONNECT, FailureType.ORDER_UNKNOWN,
    FailureType.RECONCILIATION_MISMATCH, FailureType.POSITION_MISMATCH,
    FailureType.ACCOUNTING_MISMATCH, FailureType.KILL_SWITCH,
    FailureType.STATE_CORRUPTION, FailureType.SECURITY_FAILURE,
})


def assess_failure(injection: FailureInjection) -> FailureAssessment:
    """Return a deterministic, fail-closed response; never executes recovery."""
    if not injection.strategy_id or not injection.strategy_version:
        return FailureAssessment(injection.failure, FailureResponse.HALT, False, ("strategy_identity_missing",))
    if not injection.observed:
        return FailureAssessment(injection.failure, FailureResponse.HALT, False, ("failure_not_observed",))
    if injection.failure not in _CRITICAL:
        return FailureAssessment(injection.failure, FailureResponse.HALT, False, ("unknown_failure_type",))
    if injection.failure in {FailureType.KILL_SWITCH, FailureType.SECURITY_FAILURE}:
        return FailureAssessment(injection.failure, FailureResponse.HALT, True, ("hard_safety_boundary",))
    if injection.failure in {FailureType.RECONCILIATION_MISMATCH, FailureType.POSITION_MISMATCH, FailureType.ACCOUNTING_MISMATCH, FailureType.ORDER_UNKNOWN}:
        return FailureAssessment(injection.failure, FailureResponse.RECONCILE, True, ("dependent_actions_blocked_until_reconciliation",))
    return FailureAssessment(injection.failure, FailureResponse.BLOCK, True, ("dependent_actions_blocked",))
