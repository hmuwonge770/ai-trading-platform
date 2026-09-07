from packages.autonomy.alert_delivery import AutonomousAlertDelivery


def test_delivery_window_must_be_positive():
    class Sink:
        def deliver(self, alert):
            pass

    try:
        AutonomousAlertDelivery(sink=Sink(), max_recent_keys=0)
    except ValueError as exc:
        assert "max_recent_keys" in str(exc)
    else:
        raise AssertionError("expected validation error")
