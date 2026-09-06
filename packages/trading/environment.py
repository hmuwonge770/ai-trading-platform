from __future__ import annotations

from enum import StrEnum
from urllib.parse import urlparse


class TradingEnvironment(StrEnum):
    PAPER = "paper"
    TESTNET = "testnet"
    LIVE = "live"


class EnvironmentGuard:
    """Reject unsafe environment/endpoint combinations before startup or orders."""

    LIVE_URL = "https://api.binance.com"
    TESTNET_URL = "https://testnet.binance.vision"

    @classmethod
    def validate(cls, environment: TradingEnvironment, base_url: str, *, live_armed: bool = False) -> None:
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Exchange endpoint must be an HTTPS URL")

        normalized = base_url.rstrip("/")
        if environment == TradingEnvironment.LIVE:
            if normalized != cls.LIVE_URL:
                raise RuntimeError("LIVE environment may only use the production Binance endpoint")
            if not live_armed:
                raise PermissionError("Live trading is fail-closed until explicitly armed")
        elif environment == TradingEnvironment.TESTNET:
            if normalized != cls.TESTNET_URL:
                raise RuntimeError("TESTNET environment may only use the Binance Spot Testnet endpoint")
        elif environment == TradingEnvironment.PAPER:
            if normalized in {cls.LIVE_URL, cls.TESTNET_URL}:
                raise RuntimeError("PAPER environment must not connect to Binance order endpoints")
