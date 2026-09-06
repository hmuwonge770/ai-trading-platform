from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from .domain import AuthorizationSnapshot, PromotionStage


class PreflightCode(StrEnum):
    AUTHORIZATION_MISSING = "authorization_missing"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    ENVIRONMENT_MISMATCH = "environment_mismatch"
    STRATEGY_FINGERPRINT_MISMATCH = "strategy_fingerprint_mismatch"
    STRATEGY_VERSION_MISMATCH = "strategy_version_mismatch"
    RISK_POLICY_MISMATCH = "risk_policy_mismatch"
    KILL_SWITCH = "kill_switch"
    CIRCUIT_BREAKER = "circuit_breaker"
    ALLOCATION_DISABLED = "allocation_disabled"
    CAPITAL_EXCEEDED = "capital_exceeded"
    POSITION_LIMIT_EXCEEDED = "position_limit_exceeded"
    DAILY_LOSS_EXCEEDED = "daily_loss_exceeded"
    RECONCILIATION_FAILED = "reconciliation_failed"
    ACCOUNT_UNHEALTHY = "account_unhealthy"
    MARKET_DATA_STALE = "market_data_stale"
    EXCHANGE_ENDPOINT_INVALID = "exchange_endpoint_invalid"


@dataclass(frozen=True)
class PreflightContext:
    environment: PromotionStage
    strategy_version_id: str
    strategy_fingerprint: str
    risk_policy_fingerprint: str
    kill_switch: bool
    circuit_breaker_open: bool
    allocation_enabled: bool
    allocated_capital: Decimal
    current_capital_usage: Decimal
    current_position_value: Decimal
    daily_loss: Decimal
    reconciliation_ok: bool
    account_healthy: bool
    market_data_fresh: bool
    exchange_base_url: str


@dataclass(frozen=True)
class PreflightResult:
    allowed: bool
    failures: tuple[PreflightCode, ...]


class LivePreflight:
    """Fail-closed guard immediately before an order reaches the exchange."""

    LIVE_HOSTS = {
        "https://api.binance.com",
        "https://api.binance.com/",
    }
    TESTNET_HOSTS = {
        "https://testnet.binance.vision",
        "https://testnet.binance.vision/",
    }

    def check(self, authorization: AuthorizationSnapshot | None, context: PreflightContext) -> PreflightResult:
        failures: list[PreflightCode] = []
        now = datetime.now(timezone.utc)

        if authorization is None:
            failures.append(PreflightCode.AUTHORIZATION_MISSING)
            return PreflightResult(False, tuple(failures))

        if now >= authorization.expires_at:
            failures.append(PreflightCode.AUTHORIZATION_EXPIRED)
        if authorization.environment != context.environment:
            failures.append(PreflightCode.ENVIRONMENT_MISMATCH)
        if str(authorization.strategy_version_id) != context.strategy_version_id:
            failures.append(PreflightCode.STRATEGY_VERSION_MISMATCH)
        if authorization.strategy_fingerprint != context.strategy_fingerprint:
            failures.append(PreflightCode.STRATEGY_FINGERPRINT_MISMATCH)
        if authorization.risk_policy_fingerprint != context.risk_policy_fingerprint:
            failures.append(PreflightCode.RISK_POLICY_MISMATCH)
        if context.kill_switch:
            failures.append(PreflightCode.KILL_SWITCH)
        if context.circuit_breaker_open:
            failures.append(PreflightCode.CIRCUIT_BREAKER)
        if not context.allocation_enabled:
            failures.append(PreflightCode.ALLOCATION_DISABLED)
        if context.current_capital_usage > authorization.capital_allocation.max_capital:
            failures.append(PreflightCode.CAPITAL_EXCEEDED)
        if context.current_position_value > authorization.capital_allocation.max_position_value:
            failures.append(PreflightCode.POSITION_LIMIT_EXCEEDED)
        if context.daily_loss >= authorization.capital_allocation.max_daily_loss:
            failures.append(PreflightCode.DAILY_LOSS_EXCEEDED)
        if not context.reconciliation_ok:
            failures.append(PreflightCode.RECONCILIATION_FAILED)
        if not context.account_healthy:
            failures.append(PreflightCode.ACCOUNT_UNHEALTHY)
        if not context.market_data_fresh:
            failures.append(PreflightCode.MARKET_DATA_STALE)

        expected_hosts = self.LIVE_HOSTS if context.environment in {
            PromotionStage.LIVE_CANARY,
            PromotionStage.LIVE_LIMITED,
            PromotionStage.LIVE,
        } else self.TESTNET_HOSTS
        if context.exchange_base_url not in expected_hosts:
            failures.append(PreflightCode.EXCHANGE_ENDPOINT_INVALID)

        return PreflightResult(not failures, tuple(dict.fromkeys(failures)))
