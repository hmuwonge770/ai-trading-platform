"""Fail-closed handoff boundary for human-authorized live execution.

This module does not own exchange credentials and does not implement an exchange
client. It accepts only a fresh immutable live authorization plus an already
approved deterministic risk result, then delegates to an injected submitter.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from packages.autonomy.control import AutonomousControl, AutonomousMode
from packages.autonomy.risk import AutonomousRiskResult
from packages.promotion.domain import LIVE_STAGES
from packages.trading.paper import OrderIntent

from .authorization_consumption import LiveExecutionAuthorization


class LiveExecutionSubmitter(Protocol):
    """Capability supplied by a separately controlled live adapter."""

    def submit(self, order: OrderIntent) -> object: ...


class LiveExecutionStatus(StrEnum):
    SUBMITTED = "submitted"
    BLOCKED = "blocked"
    DUPLICATE = "duplicate"


@dataclass(frozen=True, slots=True)
class LiveExecutionReport:
    status: LiveExecutionStatus
    client_order_id: str
    result: object | None
    reasons: tuple[str, ...]

    @property
    def submitted(self) -> bool:
        return self.status is LiveExecutionStatus.SUBMITTED


class AutonomousLiveExecutionBoundary:
    """Final deterministic guard before an injected live submitter."""

    def __init__(self, submitter: LiveExecutionSubmitter) -> None:
        self._submitter = submitter
        self._submitted_ids: set[str] = set()

    def submit(
        self,
        *,
        authorization: LiveExecutionAuthorization,
        risk_result: AutonomousRiskResult,
        control: AutonomousControl,
    ) -> LiveExecutionReport:
        order = risk_result.order
        reasons: list[str] = []

        if not risk_result.approved or order is None:
            reasons.append("risk_not_approved")
        if control.mode is not AutonomousMode.LIVE:
            reasons.append("control_mode_not_live")
        if not control.can_run():
            reasons.append("autonomous_control_not_runnable")
        if authorization.environment not in LIVE_STAGES:
            reasons.append("authorization_environment_not_live")
        if not authorization.authorization_hash:
            reasons.append("authorization_hash_missing")
        if order is not None:
            if order.strategy_version_id != str(authorization.strategy_version_id):
                reasons.append("strategy_version_mismatch")
            if not order.client_order_id.strip():
                reasons.append("client_order_id_missing")
            if order.client_order_id in self._submitted_ids:
                return LiveExecutionReport(
                    LiveExecutionStatus.DUPLICATE,
                    order.client_order_id,
                    None,
                    ("duplicate_client_order_id",),
                )

        if reasons or order is None:
            client_order_id = order.client_order_id if order is not None else ""
            return LiveExecutionReport(
                LiveExecutionStatus.BLOCKED,
                client_order_id,
                None,
                tuple(dict.fromkeys(reasons)),
            )

        try:
            result = self._submitter.submit(order)
        except Exception as exc:
            return LiveExecutionReport(
                LiveExecutionStatus.BLOCKED,
                order.client_order_id,
                None,
                (f"live_submitter_failed:{type(exc).__name__}",),
            )

        self._submitted_ids.add(order.client_order_id)
        return LiveExecutionReport(
            LiveExecutionStatus.SUBMITTED,
            order.client_order_id,
            result,
            (),
        )
