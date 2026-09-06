from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .domain import Promotion, PromotionStage, PromotionStatus
from .live_authorization import LiveAuthorization


PRODUCTION_BINANCE_ENDPOINT = "https://api.binance.com"


@dataclass(frozen=True, slots=True)
class FullLiveEvidence:
    canary_passed: bool = False
    limited_live_passed: bool = False
    account_healthy: bool = False
    reconciliation_healthy: bool = False
    circuit_breaker_closed: bool = False
    kill_switch_disabled: bool = False
    live_armed: bool = False
    credentials_configured: bool = False
    production_endpoint: str = PRODUCTION_BINANCE_ENDPOINT


@dataclass(frozen=True, slots=True)
class FullLiveGateReport:
    passed: bool
    failures: tuple[str, ...]

    def failures_text(self) -> str:
        return "; ".join(self.failures)


class FullLiveGate:
    """Stage 34 deterministic gate for full-live eligibility.

    This gate validates configuration and evidence only. It never loads credentials,
    submits orders, or grants exchange access.
    """

    @staticmethod
    def evaluate(
        *,
        promotion: Promotion,
        authorization: LiveAuthorization,
        strategy_version_id: str,
        strategy_fingerprint: str,
        approved_capital: Decimal,
        risk_policy_fingerprint: str,
        evidence: FullLiveEvidence,
    ) -> FullLiveGateReport:
        failures: list[str] = []

        if promotion.status not in {PromotionStatus.APPROVED, PromotionStatus.ACTIVE}:
            failures.append("Promotion is not approved or active")
        if promotion.to_stage != PromotionStage.LIVE:
            failures.append("Promotion must target LIVE")
        if not promotion.strategy_version.frozen:
            failures.append("Strategy version must be immutable")
        if str(promotion.strategy_version.strategy_version_id) != strategy_version_id:
            failures.append("Strategy version does not match promotion")
        if promotion.strategy_version.fingerprint != strategy_fingerprint:
            failures.append("Strategy fingerprint does not match promotion")
        if authorization.strategy_version_id != strategy_version_id:
            failures.append("Strategy version does not match authorization")
        if authorization.strategy_fingerprint != strategy_fingerprint:
            failures.append("Strategy fingerprint does not match authorization")
        if authorization.risk_policy_fingerprint != risk_policy_fingerprint:
            failures.append("Risk policy fingerprint does not match authorization")
        if authorization.capital != approved_capital:
            failures.append("Approved capital does not match authorization")
        if approved_capital != promotion.capital_allocation.max_capital:
            failures.append("Approved capital does not match promotion allocation")
        if not authorization.authorization_hash or len(authorization.authorization_hash) != 64:
            failures.append("Live authorization hash is invalid")
        if not evidence.canary_passed:
            failures.append("Successful canary stage is required")
        if not evidence.limited_live_passed:
            failures.append("Successful limited-live stage is required")
        if not evidence.account_healthy:
            failures.append("Account health gate has not passed")
        if not evidence.reconciliation_healthy:
            failures.append("Reconciliation health gate has not passed")
        if not evidence.circuit_breaker_closed:
            failures.append("Circuit breaker must be closed")
        if not evidence.kill_switch_disabled:
            failures.append("Kill switch must be deliberately disabled")
        if not evidence.live_armed:
            failures.append("Explicit live arm is required")
        if not evidence.credentials_configured:
            failures.append("Production credentials must be configured")
        if evidence.production_endpoint != PRODUCTION_BINANCE_ENDPOINT:
            failures.append("Production endpoint must be the approved Binance endpoint")

        return FullLiveGateReport(passed=not failures, failures=tuple(failures))


class FullLiveController:
    """Fail-closed lifecycle controller; activation requires a passed Stage 34 gate."""

    def __init__(self) -> None:
        self.active = False
        self.authorization_hash: str | None = None

    def activate(
        self,
        *,
        promotion: Promotion,
        authorization: LiveAuthorization,
        gate: FullLiveGateReport,
    ) -> None:
        if not gate.passed:
            raise PermissionError("Full-live gate has not passed: " + gate.failures_text())
        if promotion.status != PromotionStatus.APPROVED:
            raise ValueError("Promotion must be approved before full-live activation")
        if promotion.to_stage != PromotionStage.LIVE:
            raise ValueError("Full-live controller only accepts LIVE promotions")
        promotion.activate()
        self.active = True
        self.authorization_hash = authorization.authorization_hash

    def halt(self, promotion: Promotion) -> None:
        if not self.active:
            raise ValueError("Full-live is not active")
        promotion.halt()
        self.active = False
        self.authorization_hash = None

    def disarm(self) -> None:
        self.active = False
        self.authorization_hash = None
