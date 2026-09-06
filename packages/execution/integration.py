from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

from packages.promotion import PromotionStatus
from packages.risk import RiskDecision, RiskReason
from packages.trading.environment import EnvironmentGuard, TradingEnvironment
from packages.trading.paper import OrderIntent
from packages.strategies.models import MarketBar

from packages.execution.service import ExecutionResult, ExecutionService


@dataclass(frozen=True, slots=True)
class AuthorizationCheck:
    authorization_hash: str
    strategy_version_id: UUID
    environment: TradingEnvironment
    risk_policy_fingerprint: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ExecutionAuthorization:
    """Immutable authorization presented to the execution boundary."""

    authorization_hash: str
    strategy_version_id: UUID
    environment: TradingEnvironment
    risk_policy_fingerprint: str
    expires_at: datetime

    def validate(self, order: OrderIntent, *, now: datetime | None = None) -> None:
        current = now or datetime.now(timezone.utc)
        if current >= self.expires_at:
            raise PermissionError("execution authorization has expired")
        if order.strategy_version_id != str(self.strategy_version_id):
            raise PermissionError("authorization strategy version does not match the order")
        if not self.authorization_hash or len(self.authorization_hash) != 64:
            raise ValueError("authorization hash must be a SHA-256 hex digest")
        if len(self.risk_policy_fingerprint) != 64:
            raise ValueError("risk policy fingerprint must be a SHA-256 hex digest")


class AuthorizationStore:
    """Read-only persistence adapter for active promotion authorizations."""

    def __init__(self, load: Callable[[str], AuthorizationCheck | None]) -> None:
        self._load = load

    def get_active(self, authorization_hash: str, *, now: datetime | None = None) -> ExecutionAuthorization | None:
        record = self._load(authorization_hash)
        if record is None:
            return None
        current = now or datetime.now(timezone.utc)
        if current >= record.expires_at:
            return None
        return ExecutionAuthorization(
            authorization_hash=record.authorization_hash,
            strategy_version_id=record.strategy_version_id,
            environment=record.environment,
            risk_policy_fingerprint=record.risk_policy_fingerprint,
            expires_at=record.expires_at,
        )


class PromotionExecutionGateway:
    """Final deterministic gate joining promotion, environment, risk and execution.

    The gateway is deliberately downstream of AI/research. It accepts only a
    persisted authorization, validates its current promotion state through the
    supplied store, then delegates to ExecutionService, which independently
    requires a positive RiskDecision. No AI component or caller can bypass the
    risk or environment checks by invoking this boundary directly.
    """

    def __init__(self, execution: ExecutionService, authorization_store: AuthorizationStore) -> None:
        self.execution = execution
        self.authorization_store = authorization_store

    def submit(
        self,
        order: OrderIntent,
        risk_decision: RiskDecision,
        candle: MarketBar,
        *,
        authorization_hash: str,
        risk_policy_fingerprint: str,
        exchange_url: str,
        live_armed: bool = False,
        now: datetime | None = None,
    ) -> ExecutionResult:
        authorization = self.authorization_store.get_active(authorization_hash, now=now)
        if authorization is None:
            return self._rejected(order, "no active, unexpired promotion authorization")

        try:
            authorization.validate(order, now=now)
            if authorization.risk_policy_fingerprint != risk_policy_fingerprint:
                raise PermissionError("risk policy fingerprint does not match promotion authorization")
            EnvironmentGuard.validate(
                authorization.environment,
                exchange_url,
                live_armed=live_armed,
            )
        except (PermissionError, RuntimeError, ValueError) as exc:
            return self._rejected(order, str(exc))

        if not risk_decision.approved or risk_decision.reason != RiskReason.APPROVED:
            return self._rejected(order, "order was not approved by the deterministic risk gateway")

        return self.execution.submit(order, risk_decision, candle)

    @staticmethod
    def _rejected(order: OrderIntent, reason: str) -> ExecutionResult:
        return ExecutionResult(
            accepted=False,
            reason=reason,
            simulated_order=None,
            fill=None,
        )
