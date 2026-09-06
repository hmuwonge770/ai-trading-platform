from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping
from urllib.parse import urlparse


class SecurityEnvironment(StrEnum):
    PAPER = "paper"
    TESTNET = "testnet"
    LIVE = "live"


@dataclass(frozen=True, slots=True)
class SecurityPolicy:
    """Fail-closed policy for secrets and exchange access."""

    allow_live: bool = False
    allow_exchange_credentials_in_research: bool = False
    require_https: bool = True
    testnet_url: str = "https://testnet.binance.vision"
    live_url: str = "https://api.binance.com"

    def validate_endpoint(self, environment: SecurityEnvironment, base_url: str) -> None:
        parsed = urlparse(base_url)
        if self.require_https and (parsed.scheme != "https" or not parsed.netloc):
            raise ValueError("exchange endpoint must be an HTTPS URL")
        normalized = base_url.rstrip("/")
        if environment == SecurityEnvironment.PAPER:
            if normalized in {self.testnet_url, self.live_url}:
                raise PermissionError("paper environment cannot use Binance order endpoints")
            return
        if environment == SecurityEnvironment.TESTNET and normalized != self.testnet_url:
            raise PermissionError("testnet environment can only use the Binance Spot Testnet endpoint")
        if environment == SecurityEnvironment.LIVE:
            if not self.allow_live:
                raise PermissionError("live execution is disabled by security policy")
            if normalized != self.live_url:
                raise PermissionError("live environment can only use the production Binance endpoint")

    def validate_research_context(self, context: Mapping[str, Any]) -> None:
        if self.allow_exchange_credentials_in_research:
            return
        forbidden = {"api_key", "api_secret", "secret", "access_token", "private_key", "credentials"}
        leaked = sorted(str(key) for key in context if str(key).lower() in forbidden)
        if leaked:
            raise PermissionError("research context cannot contain exchange credentials or private keys")


class CredentialRedactor:
    """Redact common credential fields before logging or telemetry."""

    _SECRET_KEYS = frozenset({
        "api_key", "api_secret", "secret", "password", "token", "access_token",
        "refresh_token", "private_key", "authorization", "credentials",
    })

    @classmethod
    def redact_mapping(cls, value: Mapping[str, Any]) -> dict[str, Any]:
        return {
            str(key): "[REDACTED]" if str(key).lower() in cls._SECRET_KEYS else value_item
            for key, value_item in value.items()
        }

    @classmethod
    def redact_text(cls, value: str) -> str:
        result = value
        for marker in ("api_key=", "api_secret=", "password=", "token=", "access_token="):
            while marker in result.lower():
                lower = result.lower()
                start = lower.index(marker) + len(marker)
                end = start
                while end < len(result) and result[end] not in " &;,\n\t":
                    end += 1
                result = result[:start] + "[REDACTED]" + result[end:]
        return result
