from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from packages.autonomy.authorization_freshness import (
    AutonomousAuthorizationFreshnessGuard,
    AuthorizationFreshnessContext,
    AuthorizationFreshnessStatus,
)
from packages.promotion.domain import (
    Approval,
    ApprovalDecision,
    ApprovalRole,
    AuthorizationSnapshot,
    CapitalAllocation,
    PromotionStage,
    PromotionStatus,
)


def make_snapshot(expires_at: datetime | None = None) -> tuple[AuthorizationSnapshot, dict[str, object]]:
    strategy_version_id = uuid4()
    promotion_id = uuid4()
    fingerprint = "a" * 64
    evidence_hash = "b" * 64
    risk_fingerprint = "c" * 64
    allocation = CapitalAllocation(
        environment=PromotionStage.LIVE_CANARY,
        max_capital=Decimal("1000"),
        max_position_value=Decimal("250"),
        max_daily_loss=Decimal("50"),
        max_orders_per_day=10,
    )
    approval = Approval(
        approver_id="risk-1",
        role=ApprovalRole.RISK_MANAGER,
        decision=ApprovalDecision.APPROVE,
        fingerprint=fingerprint,
        capital_limit=allocation.max_capital,
        evidence_hash=evidence_hash,
    )
    snapshot = AuthorizationSnapshot(
        promotion_id=promotion_id,
        strategy_version_id=strategy_version_id,
        strategy_fingerprint=fingerprint,
        environment=PromotionStage.LIVE_CANARY,
        capital_allocation=allocation,
        approvals=(approval,),
        risk_policy_fingerprint=risk_fingerprint,
        evidence_snapshot_hash=evidence_hash,
        expires_at=expires_at or datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    return snapshot, {
        "promotion_id": promotion_id,
        "strategy_version_id": strategy_version_id,
        "strategy_fingerprint": fingerprint,
        "environment": PromotionStage.LIVE_CANARY,
        "risk_policy_fingerprint": risk_fingerprint,
        "evidence_snapshot_hash": evidence_hash,
    }


def make_context(snapshot: AuthorizationSnapshot, values: dict[str, object] | None = None) -> AuthorizationFreshnessContext:
    data = values or {
        "promotion_id": snapshot.promotion_id,
        "strategy_version_id": snapshot.strategy_version_id,
        "strategy_fingerprint": snapshot.strategy_fingerprint,
        "environment": snapshot.environment,
        "risk_policy_fingerprint": snapshot.risk_policy_fingerprint,
        "evidence_snapshot_hash": snapshot.evidence_snapshot_hash,
    }
    return AuthorizationFreshnessContext(
        promotion_id=data["promotion_id"],
        promotion_status=PromotionStatus.APPROVED,
        strategy_version_id=data["strategy_version_id"],
        strategy_fingerprint=data["strategy_fingerprint"],
        environment=data["environment"],
        risk_policy_fingerprint=data["risk_policy_fingerprint"],
        evidence_snapshot_hash=data["evidence_snapshot_hash"],
        now=datetime.now(timezone.utc),
    )


def test_healthy_unexpired_authorization_is_valid() -> None:
    snapshot, _ = make_snapshot()
    report = AutonomousAuthorizationFreshnessGuard().assess(snapshot, make_context(snapshot))
    assert report.status is AuthorizationFreshnessStatus.VALID
    assert report.valid
    assert report.authorization_hash == snapshot.authorization_hash


def test_expired_authorization_is_blocked() -> None:
    snapshot, _ = make_snapshot(datetime.now(timezone.utc) - timedelta(seconds=1))
    report = AutonomousAuthorizationFreshnessGuard().assess(snapshot, make_context(snapshot))
    assert report.status is AuthorizationFreshnessStatus.EXPIRED
    assert "authorization_expired" in report.reasons


@pytest.mark.parametrize(
    "field, value, reason",
    [
        ("promotion_id", uuid4(), "promotion_id_mismatch"),
        ("strategy_version_id", uuid4(), "strategy_version_mismatch"),
        ("strategy_fingerprint", "d" * 64, "strategy_fingerprint_mismatch"),
        ("risk_policy_fingerprint", "e" * 64, "risk_policy_fingerprint_mismatch"),
        ("evidence_snapshot_hash", "f" * 64, "evidence_snapshot_hash_mismatch"),
        ("environment", PromotionStage.LIVE_LIMITED, "environment_mismatch"),
    ],
)
def test_context_mismatch_blocks_authorization(field: str, value: object, reason: str) -> None:
    snapshot, values = make_snapshot()
    values[field] = value
    report = AutonomousAuthorizationFreshnessGuard().assess(snapshot, make_context(snapshot, values))
    assert report.status is AuthorizationFreshnessStatus.BLOCKED
    assert reason in report.reasons


def test_non_approved_promotion_blocks_authorization() -> None:
    snapshot, _ = make_snapshot()
    context = make_context(snapshot)
    context = AuthorizationFreshnessContext(
        promotion_id=context.promotion_id,
        promotion_status=PromotionStatus.ACTIVE,
        strategy_version_id=context.strategy_version_id,
        strategy_fingerprint=context.strategy_fingerprint,
        environment=context.environment,
        risk_policy_fingerprint=context.risk_policy_fingerprint,
        evidence_snapshot_hash=context.evidence_snapshot_hash,
        now=context.now,
    )
    report = AutonomousAuthorizationFreshnessGuard().assess(snapshot, context)
    assert report.status is AuthorizationFreshnessStatus.BLOCKED
    assert "promotion_not_approved" in report.reasons


def test_naive_now_is_rejected() -> None:
    snapshot, _ = make_snapshot()
    context = make_context(snapshot)
    context = AuthorizationFreshnessContext(
        promotion_id=context.promotion_id,
        promotion_status=context.promotion_status,
        strategy_version_id=context.strategy_version_id,
        strategy_fingerprint=context.strategy_fingerprint,
        environment=context.environment,
        risk_policy_fingerprint=context.risk_policy_fingerprint,
        evidence_snapshot_hash=context.evidence_snapshot_hash,
        now=datetime.now(),
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        AutonomousAuthorizationFreshnessGuard().assess(snapshot, context)
