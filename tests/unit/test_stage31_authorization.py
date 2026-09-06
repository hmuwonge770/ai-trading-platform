from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from packages.promotion.domain import (
    Approval,
    ApprovalDecision,
    ApprovalRole,
    AuthorizationSnapshot,
    CapitalAllocation,
    PromotionStage,
)
from packages.promotion.live_authorization import TwoPersonLiveAuthorization
from packages.promotion.readiness import ProductionReadinessGate, ReadinessEvidence, ReadinessGate


FINGERPRINT = "a" * 64
RISK_FINGERPRINT = "b" * 64
VERSION_ID = UUID(int=1)


def readiness():
    evidence = tuple(
        ReadinessEvidence(gate, True, f"evidence-{gate.value}") for gate in ReadinessGate
    )
    return ProductionReadinessGate().evaluate(
        strategy_version_id=str(VERSION_ID),
        strategy_fingerprint=FINGERPRINT,
        evidence=evidence,
    )


def snapshot():
    return AuthorizationSnapshot(
        promotion_id=uuid4(),
        strategy_version_id=VERSION_ID,
        strategy_fingerprint=FINGERPRINT,
        environment=PromotionStage.LIVE_CANARY,
        capital_allocation=CapitalAllocation(
            environment=PromotionStage.LIVE_CANARY,
            max_capital=Decimal("1000"),
            max_position_value=Decimal("100"),
            max_daily_loss=Decimal("30"),
            max_orders_per_day=10,
        ),
        approvals=(),
        risk_policy_fingerprint=RISK_FINGERPRINT,
        evidence_snapshot_hash="c" * 64,
        expires_at=datetime.now(timezone.utc),
    )


def approval(approver_id: str, role: ApprovalRole, capital=Decimal("1000")):
    return Approval(
        approver_id=approver_id,
        role=role,
        decision=ApprovalDecision.APPROVE,
        fingerprint=FINGERPRINT,
        capital_limit=capital,
        evidence_hash="d" * 64,
    )


def test_two_distinct_required_roles_produce_immutable_authorization() -> None:
    result = TwoPersonLiveAuthorization.authorize(
        readiness=readiness(),
        snapshot=snapshot(),
        approvals=(approval("risk-1", ApprovalRole.RISK_MANAGER), approval("admin-1", ApprovalRole.ADMIN)),
        requested_by="operator-1",
    )

    assert result.strategy_fingerprint == FINGERPRINT
    assert result.risk_policy_fingerprint == RISK_FINGERPRINT
    assert result.capital == Decimal("1000")
    assert result.approved_by == ("admin-1", "risk-1")


def test_requester_cannot_approve() -> None:
    with pytest.raises(PermissionError, match="Requester"):
        TwoPersonLiveAuthorization.authorize(
            readiness=readiness(), snapshot=snapshot(),
            approvals=(approval("operator-1", ApprovalRole.RISK_MANAGER), approval("admin-1", ApprovalRole.ADMIN)),
            requested_by="operator-1",
        )


def test_same_human_cannot_supply_both_roles() -> None:
    with pytest.raises(PermissionError, match="distinct"):
        TwoPersonLiveAuthorization.authorize(
            readiness=readiness(), snapshot=snapshot(),
            approvals=(approval("same-user", ApprovalRole.RISK_MANAGER), approval("same-user", ApprovalRole.ADMIN)),
            requested_by="operator-1",
        )


def test_missing_required_role_blocks_authorization() -> None:
    with pytest.raises(PermissionError, match="Risk Manager and Admin"):
        TwoPersonLiveAuthorization.authorize(
            readiness=readiness(), snapshot=snapshot(),
            approvals=(approval("risk-1", ApprovalRole.RISK_MANAGER), approval("risk-2", ApprovalRole.RISK_MANAGER)),
            requested_by="operator-1",
        )


def test_readiness_version_mismatch_blocks_authorization() -> None:
    report = ProductionReadinessGate().evaluate(
        strategy_version_id=str(uuid4()), strategy_fingerprint=FINGERPRINT,
        evidence=tuple(ReadinessEvidence(gate, True, gate.value) for gate in ReadinessGate),
    )
    with pytest.raises(ValueError, match="strategy version"):
        TwoPersonLiveAuthorization.authorize(
            readiness=report, snapshot=snapshot(),
            approvals=(approval("risk-1", ApprovalRole.RISK_MANAGER), approval("admin-1", ApprovalRole.ADMIN)),
            requested_by="operator-1",
        )


def test_strategy_change_invalidates_authorization() -> None:
    snap = snapshot()
    auth = TwoPersonLiveAuthorization.authorize(
        readiness=readiness(), snapshot=snap,
        approvals=(approval("risk-1", ApprovalRole.RISK_MANAGER), approval("admin-1", ApprovalRole.ADMIN)),
        requested_by="operator-1",
    )
    changed = "e" * 64
    assert not TwoPersonLiveAuthorization.is_unchanged(
        auth, snapshot=snap, strategy_fingerprint=changed,
        risk_policy_fingerprint=RISK_FINGERPRINT, capital=Decimal("1000")
    )


def test_capital_change_invalidates_authorization() -> None:
    snap = snapshot()
    auth = TwoPersonLiveAuthorization.authorize(
        readiness=readiness(), snapshot=snap,
        approvals=(approval("risk-1", ApprovalRole.RISK_MANAGER), approval("admin-1", ApprovalRole.ADMIN)),
        requested_by="operator-1",
    )
    assert not TwoPersonLiveAuthorization.is_unchanged(
        auth, snapshot=snap, strategy_fingerprint=FINGERPRINT,
        risk_policy_fingerprint=RISK_FINGERPRINT, capital=Decimal("1001")
    )
