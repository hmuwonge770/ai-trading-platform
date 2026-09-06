from fastapi.testclient import TestClient

from apps.api.main import app
from packages.trading.config import Settings


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_trading_defaults_are_fail_closed():
    settings = Settings()

    assert settings.trading_enabled is False
    assert settings.trading_kill_switch is True
    assert settings.trading_environment == "paper"


def test_ready_endpoint_exposes_safe_defaults():
    client = TestClient(app)
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["trading_enabled"] is False
    assert response.json()["kill_switch"] is True
