from fastapi.routing import APIRoute

from apps.api.main import app


def test_research_router_is_registered():
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    assert "/api/v1/research-sessions" in paths
    assert "/api/v1/experiments/{experiment_id}" in paths
    assert "/api/v1/market-data/{symbol}/{timeframe}/candles" in paths
