from packages.autonomy.incident_response import IncidentResponseAction
from packages.autonomy.incident_response_integration import (
    AutonomousIncidentResponseIntegration,
    IncidentResponseContext,
)


CONTEXT = IncidentResponseContext(True, True, True, True, False)


def test_integration_classifies_and_plans_response():
    decision = AutonomousIncidentResponseIntegration().evaluate(
        incident_id="incident-1",
        fingerprint="fp-1",
        code="reconciliation_gap",
        observed_at=1000,
        context=CONTEXT,
    )
    assert decision.response.action is IncidentResponseAction.CONTAIN
    assert decision.detection.observation.incident_id == "incident-1"


def test_kill_switch_produces_abort():
    context = IncidentResponseContext(True, True, True, True, True)
    decision = AutonomousIncidentResponseIntegration().evaluate(
        incident_id="incident-2",
        fingerprint="fp-2",
        code="shutdown",
        observed_at=1000,
        context=context,
    )
    assert decision.response.action is IncidentResponseAction.ABORT
    assert not decision.response.safe


def test_repeated_incident_escalates():
    decision = AutonomousIncidentResponseIntegration().evaluate(
        incident_id="incident-3",
        fingerprint="fp-3",
        code="adapter_timeout",
        observed_at=1000,
        context=CONTEXT,
        repeated_count=3,
    )
    assert decision.response.action is IncidentResponseAction.ESCALATE


def test_integration_does_not_mutate_context():
    context = CONTEXT
    AutonomousIncidentResponseIntegration().evaluate(
        incident_id="incident-4",
        fingerprint="fp-4",
        code="warning",
        observed_at=1000,
        context=context,
    )
    assert context == CONTEXT
