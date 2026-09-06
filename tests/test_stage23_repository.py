from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from packages.promotion.domain import (
    ApprovalRole,
    CapitalAllocation,
    Promotion,
    PromotionStage,
    StrategyVersion,
)
from packages.promotion.repository import PromotionRepository


class Result:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return list(self.rows)


class FakeSession:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.statements = []
        self.commits = 0

    def execute(self, statement, params=None):
        self.statements.append((str(statement), params or {}))
        return next(self.rows)

    def commit(self):
        self.commits += 1


def promotion() -> Promotion:
    version = StrategyVersion(uuid4(), uuid4(), "a" * 64, {"symbol": "BTCUSDT"})
    return Promotion(
        strategy_version=version,
        from_stage=PromotionStage.TESTNET,
        to_stage=PromotionStage.LIVE_CANARY,
        requested_by="operator",
        capital_allocation=CapitalAllocation(
            environment=PromotionStage.LIVE_CANARY,
            max_capital=Decimal("1000"),
            max_position_value=Decimal("200"),
            max_daily_loss=Decimal("50"),
            max_orders_per_day=20,
        ),
        evidence_snapshot_hash="e" * 64,
    )


def test_create_persists_promotion_and_allocation():
    db = FakeSession([Result([]), Result([])])
    p = promotion()
    assert PromotionRepository(db).create(p) == p
    assert db.commits == 1
    assert "INSERT INTO strategy_promotions" in db.statements[0][0]
    assert "INSERT INTO capital_allocations" in db.statements[1][0]


def test_get_for_update_uses_postgres_row_lock_and_rehydrates_strategy_version():
    p = promotion()
    row = {
        "id": p.promotion_id,
        "strategy_version_id": p.strategy_version.strategy_version_id,
        "from_stage": "testnet",
        "to_stage": "live_canary",
        "requested_by": "operator",
        "status": "pending",
        "required_approvals": 2,
        "evidence_snapshot_hash": "e" * 64,
        "max_capital": Decimal("1000"),
        "max_position_value": Decimal("200"),
        "max_daily_loss": Decimal("50"),
        "max_orders_per_day": 20,
        "allocation_enabled": True,
        "created_at": datetime.now(timezone.utc),
        "activated_at": None,
        "halted_at": None,
    }
    version_row = {
        "id": p.strategy_version.strategy_version_id,
        "strategy_id": p.strategy_version.strategy_id,
        "fingerprint": "a" * 64,
        "config": {"symbol": "BTCUSDT"},
    }
    db = FakeSession([Result([row]), Result([version_row]), Result([])])
    loaded = PromotionRepository(db).get_for_update(p.promotion_id)
    assert loaded is not None
    assert loaded.strategy_version.fingerprint == "a" * 64
    assert loaded.capital_allocation.max_capital == Decimal("1000")
    assert "FOR UPDATE" in db.statements[0][0]


def test_activate_locks_promotion_and_approval_rows():
    p = promotion()
    row = {
        "id": p.promotion_id,
        "strategy_version_id": p.strategy_version.strategy_version_id,
        "from_stage": "testnet", "to_stage": "live_canary", "requested_by": "operator",
        "status": "pending", "required_approvals": 2, "evidence_snapshot_hash": "e" * 64,
        "max_capital": Decimal("1000"), "max_position_value": Decimal("200"),
        "max_daily_loss": Decimal("50"), "max_orders_per_day": 20, "allocation_enabled": True,
        "created_at": datetime.now(timezone.utc), "activated_at": None, "halted_at": None,
    }
    version_row = {"id": p.strategy_version.strategy_version_id, "strategy_id": p.strategy_version.strategy_id,
                   "fingerprint": "a" * 64, "config": {"symbol": "BTCUSDT"}}
    approvals = [
        {"approver_id": "risk-1", "role": ApprovalRole.RISK_MANAGER.value, "decision": "approve",
         "fingerprint": "a" * 64, "capital_limit": Decimal("1000"), "evidence_hash": "1" * 64,
         "created_at": datetime.now(timezone.utc)},
        {"approver_id": "admin-1", "role": ApprovalRole.ADMIN.value, "decision": "approve",
         "fingerprint": "a" * 64, "capital_limit": Decimal("1000"), "evidence_hash": "2" * 64,
         "created_at": datetime.now(timezone.utc)},
    ]
    db = FakeSession([Result([row]), Result([version_row]), Result([]), Result(approvals), Result([])])
    result = PromotionRepository(db).activate(p.promotion_id)
    assert result.status.value == "active"
    assert any("FOR UPDATE" in statement for statement, _ in db.statements)
    assert db.commits == 1
