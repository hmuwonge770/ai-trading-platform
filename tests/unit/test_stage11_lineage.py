from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.experiments.lineage import (
    AntiOverfittingPolicy,
    LineageValidationError,
    dataset_fingerprint,
    lineage_fingerprint,
    validate_parent_lineage,
    validate_partition_isolation,
)
from packages.experiments.models import DatasetSplitConfig, ExperimentConfig
from packages.experiments.runner import ExperimentRunner
from packages.strategies.models import MarketBar


def candles(count: int = 10) -> list[MarketBar]:
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return [
        MarketBar(
            symbol="BTCUSDT",
            timeframe="1H",
            open_time=start + timedelta(hours=i),
            open=Decimal("100"),
            high=Decimal("101"),
            low=Decimal("99"),
            close=Decimal(str(100 + i)),
            volume=Decimal("10"),
        )
        for i in range(count)
    ]


def config(generation: int = 0, parent: str | None = None) -> ExperimentConfig:
    return ExperimentConfig(
        session_id=str(uuid4()),
        strategy_family="moving_average",
        strategy_config={"short_window": 2, "long_window": 4},
        symbol="BTCUSDT",
        timeframe="1H",
        start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
        initial_capital=Decimal("10000"),
        dataset_split=DatasetSplitConfig(),
        generation=generation,
        parent_experiment_id=parent,
    )


def test_dataset_fingerprint_is_stable_and_content_sensitive():
    data = candles()
    assert dataset_fingerprint(data) == dataset_fingerprint(data)
    changed = list(data)
    changed[-1] = MarketBar(**{**changed[-1].__dict__, "close": Decimal("999")})
    assert dataset_fingerprint(data) != dataset_fingerprint(changed)
    assert dataset_fingerprint(data) != dataset_fingerprint(list(reversed(data)))


def test_partition_isolation_rejects_overlap_and_accepts_chronological_data():
    data = candles()
    train, validation, test = ExperimentRunner.split_candles(data, config())
    validate_partition_isolation(train, validation, test)
    with pytest.raises(LineageValidationError, match="overlap"):
        validate_partition_isolation(train, validation, validation)


def test_root_lineage_requires_generation_zero():
    session_id = uuid4()
    validate_parent_lineage(
        session_id=session_id,
        generation=0,
        parent_experiment_id=None,
        parent_session_id=None,
        parent_generation=None,
    )
    with pytest.raises(LineageValidationError, match="generation 0"):
        validate_parent_lineage(
            session_id=session_id,
            generation=1,
            parent_experiment_id=None,
            parent_session_id=None,
            parent_generation=None,
        )


def test_child_lineage_requires_same_session_and_next_generation():
    session_id = uuid4()
    parent_id = uuid4()
    validate_parent_lineage(
        session_id=session_id,
        generation=1,
        parent_experiment_id=parent_id,
        parent_session_id=session_id,
        parent_generation=0,
    )
    with pytest.raises(LineageValidationError, match="same research session"):
        validate_parent_lineage(
            session_id=session_id,
            generation=1,
            parent_experiment_id=parent_id,
            parent_session_id=uuid4(),
            parent_generation=0,
        )
    with pytest.raises(LineageValidationError, match="generation \+ 1"):
        validate_parent_lineage(
            session_id=session_id,
            generation=3,
            parent_experiment_id=parent_id,
            parent_session_id=session_id,
            parent_generation=0,
        )


def test_lineage_fingerprint_is_deterministic_and_parent_sensitive():
    session_id = uuid4()
    first = lineage_fingerprint(
        session_id=session_id,
        experiment_id=None,
        parent_experiment_id=None,
        generation=0,
        strategy_fingerprint="strategy-a",
        dataset_fingerprint_value="dataset-a",
    )
    assert first == lineage_fingerprint(
        session_id=session_id,
        experiment_id=None,
        parent_experiment_id=None,
        generation=0,
        strategy_fingerprint="strategy-a",
        dataset_fingerprint_value="dataset-a",
    )
    assert first != lineage_fingerprint(
        session_id=session_id,
        experiment_id=None,
        parent_experiment_id=uuid4(),
        generation=1,
        strategy_fingerprint="strategy-a",
        dataset_fingerprint_value="dataset-a",
    )


def test_anti_overfitting_policy_is_immutable_and_bounded():
    policy = AntiOverfittingPolicy(max_experiments_per_session=2, max_generation=1)
    policy.validate_budget(existing_experiments=1, generation=1)
    with pytest.raises(LineageValidationError, match="budget"):
        policy.validate_budget(existing_experiments=2, generation=0)
    with pytest.raises(LineageValidationError, match="generation"):
        policy.validate_budget(existing_experiments=0, generation=2)
    with pytest.raises(ValidationError):
        policy.max_generation = 2
