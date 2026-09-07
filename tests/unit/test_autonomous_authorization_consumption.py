from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from packages.autonomy.authorization_consumption import (
    AutonomousLiveAuthorizationConsumer,
    AuthorizationConsumptionStatus,
)
from packages.autonomy.authorization_freshness import AuthorizationFreshnessContext
from packages.promotion.domain import (
    Approval,
    ApprovalDecision,
    ApprovalRole,
    AuthorizationRecord,
    AuthorizationSnapshot,
    CapitalAllocation,
    PromotionStage,
    PromotionStatus,
    StrategyVersion,
)


def make_fixture(*, expires_at: datetime | None = None):
    promotion_id = uuid4()
    strategy_id = uuid4()
    strategy_version_id = uuid4()
    fingerprint = "a" * 64
    evidence_hash = "b" * 64
    risk_fingerprint = "c" * 64
    expiry = expires_at or datetime.now(timezone.utc) + timedelta(minutes=5)
    strategy = StrategyVersion(strategy_version_id, strategy_id, fingerprint, {}, True)
    allocation = CapitalAllocation(PromotionStage.LIVE_CANARY, Decimal("1000"), Decimal("500"), Decimal("100"), 10)
    approvals = (
        Approval("risk", ApprovalRole.RISK_MANAGER, ApprovalDecision.APPROVE, fingerprint, Decimal("1000"), evidence_hash),
        Approval("ops", ApprovalRole.OPERATIONS, ApprovalDecision.APPROVE, fingerprint, Decimal("1000"), evidence_hash),
    )
    snapshot = AuthorizationSnapshot(
        promotion_id,
        strategy_version_id,
        fingerprint,
        PromotionStage.LIVE_CANARY,
        allocation,
        approvals,
        risk_fingerprint,
        evidence_hash,
        expiry,
    )
    record = AuthorizationRecord(
        snapshot.authorization_hash,
        PromotionStatus.APPROVED,
        strategy_version_id,
        fingerprint,
        PromotionStage.LIVE_CANARY,
        risk_fingerprint,
        expiry,
    )
    context = AuthorizationFreshnessContext(
        promotion_id,
        PromotionStatus.APPROVED,
        strategy_version_id,
        fingerprint,
        PromotionStage.LIVE_CANARY,
        risk_fingerprint,
        evidence_hash,
        datetime.now(timezone.utc),
    )
    return snapshot, record, context, strategy


def test_authorizes_matching_persisted_record():
    snapshot, record, context, _ = make_fixture()

    report = AutonomousLiveAuthorizationConsumer().assess(snapshot, record, context)

    assert report.status is AuthorizationConsumptionStatus.AUTHORIZED
    assert report.authorization is not None
    assert report.authorization.authorization_hash == snapshot.authorization_hash


def test_blocks_persisted_hash_mismatch():
    snapshot, record, context, _ = make_fixture()
    record = AuthorizationRecord(
        "d" * 64,
        record.promotion_status,
        record.strategy_version_id,
        record.strategy_fingerprint,
        record.environment,
        record.risk_policy_fingerprint,
        record.expires_at,
    )

    report = AutonomousLiveAuthorizationConsumer().assess(snapshot, record, context)

    assert report.status is AuthorizationConsumptionStatus.BLOCKED
    assert "authorization_hash_mismatch" in report.reasons


def test_expired_authorization_cannot_be_consumed():
    snapshot, record, context, _ = make_fixture(
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    report = AutonomousLiveAuthorizationConsumer().assess(snapshot, record, context)

    assert report.status is AuthorizationConsumptionStatus.EXPIRED
    assert report.authorization is None


def test_non_live_authorization_is_blocked():
    snapshot, record, context, _ = make_fixture()
    object.__setattr__(snapshot, "environment", PromotionStage.TESTNET)

    report = AutonomousLiveAuthorizationConsumer().assess(snapshot, record, context)

    assert report.status is AuthorizationConsumptionStatus.BLOCKED


def test_record_expiry_mismatch_is_blocked():
    snapshot, record, context, _ = make_fixture()
    record = AuthorizationRecord(
        record.authorization_hash,
        record.promotion_status,
        record.strategy_version_id,
        record.strategy_fingerprint,
        record.environment,
        record.risk_policy_fingerprint,
        record.expires_at + timedelta(seconds=1),
    )

    report = AutonomousLiveAuthorizationConsumer().assess(snapshot, record, context)

    assert report.status is AuthorizationConsumptionStatus.BLOCKED
    assert "persisted_expiry_mismatch" in report.reasons


def test_timezone_naive_context_fails_closed():
    snapshot, record, context, _ = make_fixture()
    naive_context = AuthorizationFreshnessContext(
        context.promotion_id,
        context.promotion_status,
        context.strategy_version_id,
        context.strategy_fingerprint,
        context.environment,
        context.risk_policy_fingerprint,
        context.evidence_snapshot_hash,
        datetime.now(),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        AutonomousLiveAuthorizationConsumer().assess(snapshot, record, naive_context)
