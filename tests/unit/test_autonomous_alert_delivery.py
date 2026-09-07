from packages.autonomy.alert_delivery import (
    AlertDeliveryStatus,
    AlertSeverity,
    AutonomousAlertDelivery,
    OperationalAlert,
)


class Sink:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.alerts = []

    def deliver(self, alert):
        if self.fail:
            raise RuntimeError("notification failure")
        self.alerts.append(alert)


def make_alert(key="auth-expired"):
    return OperationalAlert(
        alert_id="a-1",
        severity=AlertSeverity.CRITICAL,
        code="authorization_expired",
        message="Live authorization expired",
        occurred_at=1_700_000_000,
        dedupe_key=key,
    )


def test_delivers_alert_once_and_suppresses_duplicate():
    sink = Sink()
    delivery = AutonomousAlertDelivery(sink=sink)
    first = delivery.deliver(make_alert())
    second = delivery.deliver(make_alert())
    assert first.status is AlertDeliveryStatus.DELIVERED
    assert second.status is AlertDeliveryStatus.SUPPRESSED
    assert sink.alerts == [first.alert]


def test_failed_delivery_does_not_mark_alert_delivered():
    sink = Sink(fail=True)
    delivery = AutonomousAlertDelivery(sink=sink)
    report = delivery.deliver(make_alert())
    assert report.status is AlertDeliveryStatus.BLOCKED
    assert report.reason == "delivery_failed"


def test_failed_delivery_can_be_retried():
    sink = Sink(fail=True)
    delivery = AutonomousAlertDelivery(sink=sink)
    assert delivery.deliver(make_alert()).status is AlertDeliveryStatus.BLOCKED
    sink.fail = False
    assert delivery.deliver(make_alert()).status is AlertDeliveryStatus.DELIVERED


def test_recent_key_window_is_bounded():
    sink = Sink()
    delivery = AutonomousAlertDelivery(sink=sink, max_recent_keys=1)
    delivery.deliver(make_alert("one"))
    delivery.deliver(make_alert("two"))
    assert delivery.deliver(make_alert("one")).status is AlertDeliveryStatus.DELIVERED


def test_alert_validation_is_fail_closed():
    try:
        make_alert("")
    except ValueError as exc:
        assert "dedupe_key" in str(exc)
    else:
        raise AssertionError("expected invalid alert to be rejected")
