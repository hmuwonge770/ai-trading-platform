from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from .canary_gate import CanaryGateReport
from .domain import Promotion, PromotionStage, PromotionStatus


class LimitedLiveState(StrEnum):
    DISARMED = "disarmed"
    ARMED = "armed"
    ACTIVE = "active"
    HALTED = "halted"


@dataclass(frozen=True, slots=True)
class LimitedLiveLimits:
    max_capital: Decimal
    max_position_value: Decimal
    max_daily_loss: Decimal
    max_orders_per_day: int

    def validate(self) -> None:
        if self.max_capital <= 0:
            raise ValueError("max_capital must be positive")
        if self.max_position_value <= 0 or self.max_position_value > self.max_capital:
            raise ValueError("max_position_value must be positive and <= max_capital")
        if self.max_daily_loss <= 0 or self.max_daily_loss > self.max_capital:
            raise ValueError("max_daily_loss must be positive and <= max_capital")
        if self.max_orders_per_day < 1:
            raise ValueError("max_orders_per_day must be positive")


@dataclass
class LimitedLiveController:
    state: LimitedLiveState = LimitedLiveState.DISARMED
    limits: LimitedLiveLimits | None = None
    authorization_hash: str | None = None
    last_gate: CanaryGateReport | None = None

    def arm(self, promotion: Promotion, limits: LimitedLiveLimits, *, authorization_hash: str) -> None:
        if promotion.status != PromotionStatus.APPROVED:
            raise ValueError("Promotion must be approved before limited-live arming")
        if promotion.to_stage != PromotionStage.LIVE_LIMITED:
            raise ValueError("Limited-live controller only accepts LIVE_LIMITED promotions")
        if len(authorization_hash) != 64:
            raise ValueError("Authorization hash must be a SHA-256 hex digest")
        limits.validate()
        allocation = promotion.capital_allocation
        if limits.max_capital > allocation.max_capital:
            raise ValueError("Limited-live capital exceeds approved allocation")
        if limits.max_position_value > allocation.max_position_value:
            raise ValueError("Limited-live position limit exceeds approved allocation")
        if limits.max_daily_loss > allocation.max_daily_loss:
            raise ValueError("Limited-live loss limit exceeds approved allocation")
        if limits.max_orders_per_day > allocation.max_orders_per_day:
            raise ValueError("Limited-live order limit exceeds approved allocation")
        self.limits = limits
        self.authorization_hash = authorization_hash
        self.last_gate = None
        self.state = LimitedLiveState.ARMED

    def start(self, promotion: Promotion, *, gate: CanaryGateReport) -> None:
        if self.state != LimitedLiveState.ARMED or self.limits is None or self.authorization_hash is None:
            raise ValueError("Limited-live must be armed before activation")
        if promotion.status != PromotionStatus.APPROVED:
            raise ValueError("Promotion must remain approved before limited-live activation")
        if not gate.passed:
            raise PermissionError("Limited-live gate has not passed: " + "; ".join(gate.failures()))
        promotion.activate()
        self.last_gate = gate
        self.state = LimitedLiveState.ACTIVE

    def halt(self, promotion: Promotion) -> None:
        if self.state != LimitedLiveState.ACTIVE:
            raise ValueError("Limited-live is not active")
        promotion.halt()
        self.state = LimitedLiveState.HALTED

    def disarm(self) -> None:
        self.state = LimitedLiveState.DISARMED
        self.limits = None
        self.authorization_hash = None
        self.last_gate = None

    def scale(self, *, new_limits: LimitedLiveLimits, gate: CanaryGateReport) -> None:
        if self.state != LimitedLiveState.ACTIVE:
            raise ValueError("Only active limited-live can be scaled")
        if not gate.passed:
            raise PermissionError("Scaling gate has not passed: " + "; ".join(gate.failures()))
        if self.limits is None:
            raise ValueError("Limited-live limits are missing")
        new_limits.validate()
        if new_limits.max_capital < self.limits.max_capital:
            raise ValueError("Use a reduction operation for decreasing capital")
        self.limits = new_limits
        self.last_gate = gate
