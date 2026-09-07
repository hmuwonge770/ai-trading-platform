from packages.autonomy.incident_lifecycle import Incident, IncidentLifecycle, IncidentSeverity, IncidentStatus


class Store:
    def __init__(self):
        self.items = {}

    def save(self, incident):
        self.items[incident.incident_id] = incident

    def get(self, incident_id):
        return self.items.get(incident_id)


def make_incident():
    return Incident("i-1", "authorization-expired", IncidentSeverity.CRITICAL, "authorization_expired", 100)


def test_incident_transitions_are_monotonic():
    store = Store()
    lifecycle = IncidentLifecycle(store=store)
    incident = make_incident()
    acknowledged = lifecycle.transition(incident, IncidentStatus.ACKNOWLEDGED, occurred_at=110)
    escalated = lifecycle.transition(acknowledged, IncidentStatus.ESCALATED, occurred_at=120)
    resolved = lifecycle.transition(escalated, IncidentStatus.RESOLVED, occurred_at=130)
    assert resolved.status is IncidentStatus.RESOLVED
    assert resolved.acknowledged_at == 110
    assert resolved.resolved_at == 130


def test_resolved_incident_cannot_reopen():
    store = Store()
    lifecycle = IncidentLifecycle(store=store)
    resolved = lifecycle.transition(make_incident(), IncidentStatus.RESOLVED, occurred_at=110)
    try:
        lifecycle.transition(resolved, IncidentStatus.OPEN, occurred_at=120)
    except ValueError as exc:
        assert "invalid incident transition" in str(exc)
    else:
        raise AssertionError("expected reopening to be rejected")


def test_transition_timestamp_must_not_precede_opening():
    lifecycle = IncidentLifecycle(store=Store())
    try:
        lifecycle.transition(make_incident(), IncidentStatus.RESOLVED, occurred_at=99)
    except ValueError as exc:
        assert "precede" in str(exc)
    else:
        raise AssertionError("expected timestamp validation")


def test_invalid_incident_is_rejected():
    try:
        Incident("", "fp", IncidentSeverity.WARNING, "x", 100)
    except ValueError as exc:
        assert "identity" in str(exc)
    else:
        raise AssertionError("expected invalid incident")
