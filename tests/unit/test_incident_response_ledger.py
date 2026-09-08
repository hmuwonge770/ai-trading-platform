import pytest

from packages.autonomy.incident_response import (
    IncidentResponseAction,
    IncidentResponseReport,
)
from packages.autonomy.incident_response_ledger import (
    IdempotentIncidentResponseLedger,
    InMemoryIncidentDecisionStore,
)


def report(action=IncidentResponseAction.CONTAIN):
    return IncidentResponseReport("incident-1", "fp-1", action, action is not IncidentResponseAction.ABORT, ("reason",))


def test_first_record_is_not_replayed():
    result = IdempotentIncidentResponseLedger(store=InMemoryIncidentDecisionStore()).record(report())
    assert not result.replayed


def test_duplicate_record_is_replayed():
    ledger = IdempotentIncidentResponseLedger(store=InMemoryIncidentDecisionStore())
    ledger.record(report())
    result = ledger.record(report())
    assert result.replayed
    assert result.report == report()


def test_conflicting_fingerprint_is_rejected():
    ledger = IdempotentIncidentResponseLedger(store=InMemoryIncidentDecisionStore())
    ledger.record(report())
    with pytest.raises(ValueError, match="conflict|different decision"):
        ledger.record(report(IncidentResponseAction.ESCALATE))
