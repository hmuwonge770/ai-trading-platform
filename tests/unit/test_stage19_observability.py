from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from apps.api.main import app
from packages.observability.metrics import TradingMetrics


def test_metrics_collect_domain_counters_with_bounded_labels() -> None:
    observed = TradingMetrics(CollectorRegistry())
    observed.observe_risk("approved", "approved")
    observed.observe_execution("filled")
    observed.observe_exchange_error("place_market_order")
    observed.observe_accounting_transaction("trade")

    payload = observed.exposition().decode()
    assert "trading_risk_decisions_total" in payload
    assert 'decision="approved"' in payload
    assert "trading_execution_outcomes_total" in payload
    assert 'status="filled"' in payload
    assert "trading_exchange_errors_total" in payload
    assert 'operation="place_market_order"' in payload
    assert "trading_accounting_transactions_total" in payload
    assert 'transaction_type="trade"' in payload


def test_metrics_endpoint_is_exposed() -> None:
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "trading_http_requests_total" in response.text


def test_http_metrics_use_route_templates_not_dynamic_paths() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    payload = client.get("/metrics").text
    assert 'route="/health"' in payload
