from packages.autonomy.incident_lifecycle import Incident, IncidentSeverity, IncidentStatus


def test_incident_is_immutable_and_persistable():
    incident = Incident("i-1", "fp", IncidentSeverity.WARNING, "adapter_unhealthy", 100)
    assert incident.status is IncidentStatus.OPEN
    assert incident.incident_id == "i-1"
    try:
        incident.status = IncidentStatus.RESOLVED
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("incident must remain immutable")
