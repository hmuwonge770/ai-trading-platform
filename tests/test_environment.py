import pytest

from packages.trading.environment import EnvironmentGuard, TradingEnvironment


def test_live_is_fail_closed_by_default():
    with pytest.raises(PermissionError):
        EnvironmentGuard.validate(TradingEnvironment.LIVE, EnvironmentGuard.LIVE_URL)


def test_live_requires_production_endpoint():
    with pytest.raises(RuntimeError):
        EnvironmentGuard.validate(TradingEnvironment.LIVE, EnvironmentGuard.TESTNET_URL, live_armed=True)


def test_testnet_cannot_use_production_endpoint():
    with pytest.raises(RuntimeError):
        EnvironmentGuard.validate(TradingEnvironment.TESTNET, EnvironmentGuard.LIVE_URL)


def test_paper_cannot_use_binance_order_endpoints():
    with pytest.raises(RuntimeError):
        EnvironmentGuard.validate(TradingEnvironment.PAPER, EnvironmentGuard.LIVE_URL)
    with pytest.raises(RuntimeError):
        EnvironmentGuard.validate(TradingEnvironment.PAPER, EnvironmentGuard.TESTNET_URL)


def test_live_requires_https():
    with pytest.raises(ValueError):
        EnvironmentGuard.validate(TradingEnvironment.LIVE, "http://api.binance.com", live_armed=True)
