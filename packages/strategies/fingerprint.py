from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def strategy_fingerprint(family: str, config: BaseModel | dict[str, Any]) -> str:
    """Create a stable SHA-256 fingerprint from strategy family and configuration."""
    if isinstance(config, BaseModel):
        payload = config.model_dump(mode="json")
    else:
        payload = config

    canonical = json.dumps(
        {"family": family, "config": payload},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
