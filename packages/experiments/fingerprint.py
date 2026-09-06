from __future__ import annotations

import hashlib
import json
from typing import Any

from packages.experiments.models import ExperimentConfig


def experiment_fingerprint(
    config: ExperimentConfig, dataset_fingerprint: str | None = None
) -> str:
    """Return a stable identity for every material experiment input."""
    payload: dict[str, Any] = {
        "session_id": config.session_id,
        "strategy_family": config.strategy_family,
        "strategy_config": config.strategy_config,
        "dataset": config.dataset_config(),
        "dataset_fingerprint": dataset_fingerprint,
        "initial_capital": str(config.initial_capital),
        "fee_rate": str(config.fee_rate),
        "slippage_rate": str(config.slippage_rate),
        "engine_version": config.engine_version,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
