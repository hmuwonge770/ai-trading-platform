from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .canary_gate import CanaryGateReport
from .domain import Promotion, PromotionStage, PromotionStatus


class CanaryState(StrEnum):
    DISARMED = "disarmed"
    ARMED = "armed"
    ACTIVE = "active"
    HALTED = "halted"


@dataclass(frozen=True)
class CanaryLimits:
    max_capital: Decimal
    max_position_value: Decimal
    max_daily_loss: Decimal
    max_orders_per_day: int


@dataclass
class CanaryController:
    state: CanaryState = CanaryState.DISARMED
    limits: CanaryLimits | None = None
    authorization_hash: str | None = None
    last_gate: CanaryGateReport | None = None

    def arm(self, promotion: Promotion, limits: CanaryLimits, *, authorization_hash: str) -> None:
        if promotion.status != PromotionStatus.APPROVED:
            raise ValueError("Promotion must be approved before canary arming")
        if promotion.to_stage != PromotionStage.LIVE_CANARY:
            raise ValueError("Canary controller only accepts LIVE_CANARY promotions")
        if len(authorization_hash) != 64:
            raise ValueError("Canary authorization hash must be a SHA-256 hex digest")
        if limits.max_capital > promotion.capital_allocation.max_capital:
            raise ValueError("Canary capital exceeds approved allocation")
        if limits.max_position_value > promotion.capital_allocation.max_position_value:
            raise ValueError("Canary position limit exceeds approved allocation")
        if limits.max_daily_loss > promotion.capital_allocation.max_daily_loss:
            raise ValueError("Canary loss limit exceeds approved allocation")
        if limits.max_orders_per_day > promotion.capital_allocation.max_orders_per_day:
            raise ValueError("Canary order limit exceeds approved allocation")
        self.limits = limits
        self.authorization_hash = authorization_hash
        self.last_gate = None
        self.state = CanaryState.ARMED

    def start(self, promotion: Promotion, *, gate: CanaryGateReport) -> None:
        if self.state != CanaryState.ARMED or self.limits is None or self.authorization_hash is None:
            raise ValueError("Canary must be armed before activation")
        if promotion.status != PromotionStatus.APPROVED:
            raise ValueError("Promotion must remain approved before canary activation")
        if not gate.passed:
            raise PermissionError("Canary gate has not passed: " + "; ".join(gate.failures()))
        promotion.activate()
        self.last_gate = gate
        self.state = CanaryState.ACTIVE

    def halt(self, promotion: Promotion) -> None:
        if self.state != CanaryState.ACTIVE:
            raise ValueError("Canary is not active")
        promotion.halt()
        self.state = CanaryState.HALTED

    def disarm(self) -> None:
        self.state = CanaryState.DISARMED
        self.limits = None
        self.authorization_hash = None
        self.last_gate = None

    def scale(self, *, new_limits: CanaryLimits, canary_gate: CanaryGateReport) -> None:
        if self.state != CanaryState.ACTIVE:
            raise ValueError("Only an active canary can be scaled")
        if not canary_gate.passed:
            raise PermissionError("Canary gate has not passed: " + "; ".join(canary_gate.failures()))
        if self.limits is None:
            raise ValueError("Canary limits are missing")
        if new_limits.max_capital < self.limits.max_capital:
            raise ValueError("Use a reduction operation for decreasing capital")
        self.last_gate = canary_gate
        self.limits = new_limits
