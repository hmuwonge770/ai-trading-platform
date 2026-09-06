from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Sequence
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from packages.strategies.models import MarketBar


class LineageValidationError(ValueError):
    """Raised when research lineage or dataset isolation is invalid."""


def _canonical_hash(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def dataset_fingerprint(candles: Sequence[MarketBar]) -> str:
    """Return a stable content hash for the exact ordered research dataset."""
    if not candles:
        raise LineageValidationError("cannot fingerprint an empty dataset")
    payload = [
        {
            "symbol": candle.symbol,
            "timeframe": candle.timeframe,
            "open_time": candle.open_time.isoformat(),
            "open": str(candle.open),
            "high": str(candle.high),
            "low": str(candle.low),
            "close": str(candle.close),
            "volume": str(candle.volume),
        }
        for candle in candles
    ]
    return _canonical_hash(payload)


def lineage_fingerprint(
    *,
    session_id: str | uuid.UUID,
    experiment_id: str | uuid.UUID | None,
    parent_experiment_id: str | uuid.UUID | None,
    generation: int,
    strategy_fingerprint: str,
    dataset_fingerprint_value: str | None,
) -> str:
    """Hash the immutable ancestry and research inputs of an experiment."""
    return _canonical_hash(
        {
            "session_id": str(session_id),
            "experiment_id": str(experiment_id) if experiment_id else None,
            "parent_experiment_id": str(parent_experiment_id) if parent_experiment_id else None,
            "generation": generation,
            "strategy_fingerprint": strategy_fingerprint,
            "dataset_fingerprint": dataset_fingerprint_value,
        }
    )


def validate_parent_lineage(
    *,
    session_id: uuid.UUID,
    generation: int,
    parent_experiment_id: uuid.UUID | None,
    parent_session_id: uuid.UUID | None,
    parent_generation: int | None,
    experiment_id: uuid.UUID | None = None,
) -> None:
    """Enforce a single-session, strictly increasing experiment genealogy."""
    if generation < 0:
        raise LineageValidationError("generation cannot be negative")
    if experiment_id is not None and parent_experiment_id == experiment_id:
        raise LineageValidationError("an experiment cannot be its own parent")
    if parent_experiment_id is None:
        if generation != 0:
            raise LineageValidationError("root experiments must have generation 0")
        return
    if parent_session_id is None or parent_generation is None:
        raise LineageValidationError("parent experiment must exist before creating a child")
    if parent_session_id != session_id:
        raise LineageValidationError("parent experiment must belong to the same research session")
    if generation != parent_generation + 1:
        raise LineageValidationError("child generation must equal parent generation + 1")


def validate_partition_isolation(
    train: Sequence[MarketBar], validation: Sequence[MarketBar], test: Sequence[MarketBar]
) -> None:
    """Verify chronological, non-overlapping partitions before any backtest."""
    partitions = (("train", train), ("validation", validation), ("test", test))
    if any(not candles for _, candles in partitions):
        raise LineageValidationError("train, validation, and test partitions must be non-empty")
    identities = [
        (candle.symbol, candle.timeframe, candle.open_time)
        for _, candles in partitions
        for candle in candles
    ]
    if len(identities) != len(set(identities)):
        raise LineageValidationError("dataset partitions overlap")
    for name, candles in partitions:
        for index in range(1, len(candles)):
            if candles[index].open_time <= candles[index - 1].open_time:
                raise LineageValidationError(f"{name} partition must be strictly chronological")
    if train[-1].open_time >= validation[0].open_time:
        raise LineageValidationError("training data overlaps or follows validation data")
    if validation[-1].open_time >= test[0].open_time:
        raise LineageValidationError("validation data overlaps or follows final-test data")


def split_counts(total: int, train_ratio: Decimal, validation_ratio: Decimal) -> tuple[int, int, int]:
    """Calculate deterministic non-empty chronological partition sizes."""
    if total < 3:
        raise LineageValidationError("at least three candles are required for train/validation/test")
    train_count = max(1, int(total * train_ratio))
    validation_count = max(1, int(total * validation_ratio))
    if train_count + validation_count >= total:
        train_count = max(1, total - 2)
        validation_count = 1
    return train_count, validation_count, total - train_count - validation_count


class AntiOverfittingPolicy(BaseModel):
    """Explicit research-budget limits that prevent unbounded tuning loops."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    max_experiments_per_session: int = Field(default=100, ge=1)
    max_generation: int = Field(default=10, ge=0)

    def validate_budget(self, *, existing_experiments: int, generation: int) -> None:
        if existing_experiments >= self.max_experiments_per_session:
            raise LineageValidationError("research session experiment budget has been exhausted")
        if generation > self.max_generation:
            raise LineageValidationError("experiment generation exceeds the research budget")
