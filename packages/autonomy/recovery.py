"""Fail-closed reliability and recovery decisions for autonomous trading.

The recovery engine plans bounded responses to operational faults. It never
bypasses risk, reconciliation, authorization, or the autonomous kill switch.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RecoveryEvent(StrEnum):
    SUCCESS = "success"
    MARKET_STALE = "market_stale"
    EXECUTION_ERROR = "execution_error"
    RECONCILIATION_MISMATCH = "reconciliation_mismatch"
    UNKNOWN_FAILURE = "unknown_failure"


class RecoveryAction(StrEnum):
    CONTINUE = "continue"
    RETRY = "retry"
    HALT = "halt"


@dataclass(frozen=True, slots=True)
class RecoveryPolicy:
    max_consecutive_failures: int = 3
    max_retries: int = 2
    market_stale_after_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_consecutive_failures < 1:
            raise ValueError("max_consecutive_failures must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.market_stale_after_seconds <= 0:
            raise ValueError("market_stale_after_seconds must be positive")


@dataclass(frozen=True, slots=True)
class RecoveryState:
    consecutive_failures: int = 0
    retries: int = 0
    halted: bool = False


@dataclass(frozen=True, slots=True)
class RecoveryDecision:
    action: RecoveryAction
    reason: str
    state: RecoveryState


class AutonomousRecoveryEngine:
    """Produce bounded, fail-closed recovery decisions."""

    def __init__(self, policy: RecoveryPolicy | None = None) -> None:
        self.policy = policy or RecoveryPolicy()
        self._state = RecoveryState()

    @property
    def state(self) -> RecoveryState:
        return self._state

    def observe(
        self,
        event: RecoveryEvent,
        *,
        market_age_seconds: float | None = None,
    ) -> RecoveryDecision:
        if self._state.halted:
            return RecoveryDecision(RecoveryAction.HALT, "already_halted", self._state)

        if event is RecoveryEvent.SUCCESS:
            self._state = RecoveryState()
            return RecoveryDecision(RecoveryAction.CONTINUE, "healthy", self._state)

        if event is RecoveryEvent.RECONCILIATION_MISMATCH:
            return self._halt("reconciliation_mismatch")

        if event is RecoveryEvent.MARKET_STALE:
            if market_age_seconds is None:
                return self._halt("market_age_unknown")
            if market_age_seconds < 0:
                return self._halt("market_age_invalid")
            if market_age_seconds <= self.policy.market_stale_after_seconds:
                return self._continue("market_fresh")
            return self._halt("market_data_stale")

        failures = self._state.consecutive_failures + 1
        retries = self._state.retries
        self._state = RecoveryState(failures, retries, False)

        if failures >= self.policy.max_consecutive_failures:
            return self._halt("failure_threshold_reached")
        if event is RecoveryEvent.UNKNOWN_FAILURE:
            return self._halt("unknown_failure")
        if retries >= self.policy.max_retries:
            return self._halt("retry_budget_exhausted")

        self._state = RecoveryState(failures, retries + 1, False)
        return RecoveryDecision(RecoveryAction.RETRY, "bounded_retry", self._state)

    def reset_after_reconciliation(self) -> RecoveryDecision:
        """Clear a halt only after an external reconciliation has succeeded."""
        if not self._state.halted:
            return RecoveryDecision(RecoveryAction.CONTINUE, "not_halted", self._state)
        self._state = RecoveryState()
        return RecoveryDecision(RecoveryAction.CONTINUE, "reconciled_and_reset", self._state)

    def _halt(self, reason: str) -> RecoveryDecision:
        self._state = RecoveryState(
            self._state.consecutive_failures,
            self._state.retries,
            True,
        )
        return RecoveryDecision(RecoveryAction.HALT, reason, self._state)

    def _continue(self, reason: str) -> RecoveryDecision:
        return RecoveryDecision(RecoveryAction.CONTINUE, reason, self._state)
