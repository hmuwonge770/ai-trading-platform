"""Fail-closed autonomous order lifecycle recovery contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class OrderLifecycleState(StrEnum):
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class OrderRecoveryEvent(StrEnum):
    ACKNOWLEDGED = "acknowledged"
    PARTIAL_FILL = "partial_fill"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    RESPONSE_LOST = "response_lost"
    CONFIRMED_NOT_FOUND = "confirmed_not_found"
    QUERY_FAILED = "query_failed"


class OrderRecoveryAction(StrEnum):
    CONTINUE = "continue"
    RECONCILE = "reconcile"
    RETRY_SUBMISSION = "retry_submission"
    HALT = "halt"


@dataclass(frozen=True, slots=True)
class OrderRecoveryPolicy:
    max_resubmissions: int = 1

    def __post_init__(self) -> None:
        if self.max_resubmissions < 0:
            raise ValueError("max_resubmissions must be non-negative")


@dataclass(frozen=True, slots=True)
class OrderRecoveryReport:
    state: OrderLifecycleState
    action: OrderRecoveryAction
    reason: str
    resubmissions: int


class AutonomousOrderLifecycleRecovery:
    """Recover ambiguous orders only after exchange state is positively known."""

    _terminal = {
        OrderLifecycleState.FILLED,
        OrderLifecycleState.CANCELED,
        OrderLifecycleState.REJECTED,
    }

    def __init__(
        self,
        *,
        client_order_id: str,
        policy: OrderRecoveryPolicy | None = None,
        initial_state: OrderLifecycleState = OrderLifecycleState.SUBMITTED,
    ) -> None:
        if not client_order_id.strip():
            raise ValueError("client_order_id must not be empty")
        self.client_order_id = client_order_id
        self.policy = policy or OrderRecoveryPolicy()
        self._state = initial_state
        self._resubmissions = 0

    @property
    def state(self) -> OrderLifecycleState:
        return self._state

    def observe(self, event: OrderRecoveryEvent) -> OrderRecoveryReport:
        if self._state in self._terminal:
            return self._report(OrderRecoveryAction.CONTINUE, "terminal_order_state")

        if event is OrderRecoveryEvent.ACKNOWLEDGED:
            self._state = OrderLifecycleState.ACKNOWLEDGED
            return self._report(OrderRecoveryAction.CONTINUE, "order_acknowledged")
        if event is OrderRecoveryEvent.PARTIAL_FILL:
            self._state = OrderLifecycleState.PARTIALLY_FILLED
            return self._report(OrderRecoveryAction.CONTINUE, "partial_fill_observed")
        if event is OrderRecoveryEvent.FILLED:
            self._state = OrderLifecycleState.FILLED
            return self._report(OrderRecoveryAction.CONTINUE, "order_filled")
        if event is OrderRecoveryEvent.CANCELED:
            self._state = OrderLifecycleState.CANCELED
            return self._report(OrderRecoveryAction.CONTINUE, "order_canceled")
        if event is OrderRecoveryEvent.REJECTED:
            self._state = OrderLifecycleState.REJECTED
            return self._report(OrderRecoveryAction.CONTINUE, "order_rejected")

        if event in {OrderRecoveryEvent.RESPONSE_LOST, OrderRecoveryEvent.QUERY_FAILED}:
            self._state = OrderLifecycleState.UNKNOWN
            return self._report(OrderRecoveryAction.RECONCILE, "order_state_uncertain")

        if event is OrderRecoveryEvent.CONFIRMED_NOT_FOUND:
            if self._state is not OrderLifecycleState.UNKNOWN:
                return self._report(OrderRecoveryAction.HALT, "not_found_without_uncertainty")
            if self._resubmissions >= self.policy.max_resubmissions:
                return self._report(OrderRecoveryAction.HALT, "resubmission_budget_exhausted")
            self._resubmissions += 1
            self._state = OrderLifecycleState.SUBMITTED
            return self._report(OrderRecoveryAction.RETRY_SUBMISSION, "exchange_confirmed_order_absent")

        return self._report(OrderRecoveryAction.HALT, "unsupported_recovery_event")

    def _report(self, action: OrderRecoveryAction, reason: str) -> OrderRecoveryReport:
        return OrderRecoveryReport(self._state, action, reason, self._resubmissions)
