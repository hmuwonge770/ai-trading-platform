import pytest

from packages.autonomy.autonomous_lifecycle_validation import LifecycleValidationAssessment, LifecycleValidationAction
from packages.autonomy.autonomous_lifecycle_validation_ledger import InMemoryLifecycleValidationLedger


def assessment(action=LifecycleValidationAction.PASS, safe=True, reasons=()):
    return LifecycleValidationAssessment(action, safe, reasons)


def test_ledger_is_idempotent():
    ledger = InMemoryLifecycleValidationLedger()
    first = ledger.record("strategy-1", "run-1", assessment())
    second = ledger.record("strategy-1", "run-1", assessment())
    assert first == second


def test_ledger_rejects_conflicting_replay():
    ledger = InMemoryLifecycleValidationLedger()
    ledger.record("strategy-1", "run-1", assessment())
    with pytest.raises(ValueError, match="conflicting"):
        ledger.record("strategy-1", "run-1", assessment(LifecycleValidationAction.BLOCK, False, ("x",)))


def test_ledger_binds_identity():
    ledger = InMemoryLifecycleValidationLedger()
    ledger.record("strategy-1", "run-1", assessment())
    assert ledger.get("strategy-2", "run-1") is None


def test_ledger_requires_identity_and_request_key():
    ledger = InMemoryLifecycleValidationLedger()
    with pytest.raises(ValueError):
        ledger.record("", "run-1", assessment())
    with pytest.raises(ValueError):
        ledger.record("strategy-1", "", assessment())
