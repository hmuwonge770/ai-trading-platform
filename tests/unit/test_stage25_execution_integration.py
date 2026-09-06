from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from packages.execution import (
    AuthorizationStore,
    ExecutionConfig,
    ExecutionSimulator,
    ExecutionService,
    PromotionExecutionGateway,
)
from packages.promotion import AuthorizationRecord, PromotionStatus, PromotionStage
from packages.risk import RiskDecision, RiskReason
from packages.strategies.models import MarketBar, Signal
from packages.trading.environment import EnvironmentGuard
from packages.trading.paper import OrderIntent


STRATEGY_VERSION_ID = uuid4()
STRATEGY_FINGERPRINT = "a" * 64
RISK_FINGERPRINT = "b" * 64
AUTH_HASH = "c" * 64
NOW = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def order() -> OrderIntent:
    return OrderIntent(
        intent_id=uuid4(), signal_id=uuid4(), strategy_version_id=str(STRATEGY_VERSION_ID),
        symbol="BTCUSDT", timeframe="1m", side=Signal.BUY, quantity=Decimal("1"),
        reference_price=Decimal("100"), client_order_id="client-25", reason="test",
    )
