from decimal import Decimal

import pytest

from packages.autonomy.production_operation import (
    ProductionOperationAssessment,
    ProductionOperationAction,
)
from packages.autonomy.production_operation_ledger import (
    InMemoryProductionOperationLedger,
    ProductionOperationDecision,
)


def assessment() -> ProductionOperationAssessment:
    return ProductionOperationAssessment(
        action=ProductionOperationAction.OPERATE,
        reasons=(),
        strategy_version_id="strategy-v1",
        strategy_fingerprint="fingerprint-1",
    )


def test_decision_digest_is_deterministic() -> None:
    first = ProductionOperationDecision.create(
        strategy_version_id="strategy-v1",
        strategy_fingerprint="fingerprint-1",
        revision=1,
        assessment=assessment(),
    )
    second = ProductionOperationDecision.create(
        strategy_version_id="strategy-v1",
        strategy_fingerprint="fingerprint-1",
        revision=1,
        assessment=assessment(),
    )
    assert first.digest == second.digest


def test_ledger_is_idempotent_for_same_decision() -> None:
    ledger = InMemoryProductionOperationLedger()
    decision = ProductionOperationDecision.create(
        strategy_version_id="strategy-v1",
        strategy_fingerprint="fingerprint-1",
        revision=1,
        assessment=assessment(),
    )
    assert ledger.record(decision) == decision
    assert ledger.record(decision) == decision
    assert ledger.get(
        strategy_version_id="strategy-v1",
        strategy_fingerprint="fingerprint-1",
        revision=1,
    ) == decision


def test_ledger_rejects_conflicting_decision() -> None:
    ledger = InMemoryProductionOperationLedger()
    first = ProductionOperationDecision.create(
        strategy_version_id="strategy-v1",
        strategy_fingerprint="fingerprint-1",
        revision=1,
        assessment=assessment(),
    )
    conflicting = ProductionOperationAssessment(
        action=ProductionOperationAction.HALT,
        reasons=("risk_governance_not_approved",),
        strategy_version_id="strategy-v1",
        strategy_fingerprint="fingerprint-1",
    )
    second = ProductionOperationDecision.create(
        strategy_version_id="strategy-v1",
        strategy_fingerprint="fingerprint-1",
        revision=1,
        assessment=conflicting,
    )
    ledger.record(first)
    with pytest.raises(ValueError, match="conflicting"):
        ledger.record(second)


def test_decision_requires_identity_and_nonnegative_revision() -> None:
    with pytest.raises(ValueError):
        ProductionOperationDecision.create(
            strategy_version_id="",
            strategy_fingerprint="fingerprint-1",
            revision=1,
            assessment=assessment(),
        )
    with pytest.raises(ValueError):
        ProductionOperationDecision.create(
            strategy_version_id="strategy-v1",
            strategy_fingerprint="fingerprint-1",
            revision=-1,
            assessment=assessment(),
        )
