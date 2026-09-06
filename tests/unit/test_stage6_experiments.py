from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from packages.experiments.fingerprint import experiment_fingerprint
from packages.experiments.models import DatasetSplitConfig, ExperimentConfig
from packages.experiments.runner import ExperimentRunner
from packages.strategies.models import MarketBar


START = datetime(2025, 1, 1, tzinfo=timezone.utc)


def config(**overrides) -> ExperimentConfig:
    values = {
        "session_id": "00000000-0000-0000-0000-000000000001",
        "strategy_family": "moving_average_crossover",
        "strategy_config": {"short_window": 3, "long_window": 5},
        "symbol": "btcusdt",
        "timeframe": "1h",
        "start_time": START,
        "end_time": START + timedelta(hours=20),
        "initial_capital": Decimal("1000"),
    }
    values.update(overrides)
    return ExperimentConfig(**values)


def candles(count: int = 20) -> tuple[MarketBar, ...]:
    return tuple(
        MarketBar(
            symbol="BTCUSDT",
            timeframe="1h",
            open_time=START + timedelta(hours=index),
            open=Decimal("100") + index,
            high=Decimal("101") + index,
            low=Decimal("99") + index,
            close=Decimal("100") + index,
            volume=Decimal("10"),
        )
        for index in range(count)
    )


def test_experiment_fingerprint_is_stable_and_material():
    first = experiment_fingerprint(config())
    second = experiment_fingerprint(config())
    changed = experiment_fingerprint(config(strategy_config={"short_window": 2, "long_window": 5}))

    assert first == second
    assert first != changed
    assert len(first) == 64


def test_dataset_split_defaults_to_chronological_60_20_20():
    train, validation, test = ExperimentRunner.split_candles(candles(), config())

    assert len(train) == 12
    assert len(validation) == 4
    assert len(test) == 4
    assert train[-1].open_time < validation[0].open_time < test[0].open_time


def test_dataset_split_has_no_overlap():
    train, validation, test = ExperimentRunner.split_candles(candles(10), config())

    timestamps = [bar.open_time for bar in (*train, *validation, *test)]
    assert len(timestamps) == len(set(timestamps))
    assert len(train) + len(validation) + len(test) == 10


def test_dataset_split_rejects_too_small_dataset():
    with pytest.raises(ValueError, match="at least three candles"):
        ExperimentRunner.split_candles(candles(2), config())


def test_dataset_split_preserves_custom_proportions():
    custom = config(
        dataset_split=DatasetSplitConfig(train=Decimal("0.50"), validation=Decimal("0.30"), test=Decimal("0.20"))
    )
    train, validation, test = ExperimentRunner.split_candles(candles(20), custom)

    assert (len(train), len(validation), len(test)) == (10, 6, 4)


def test_config_rejects_invalid_window_and_timezone():
    with pytest.raises(ValueError, match="start_time must be before end_time"):
        config(start_time=START + timedelta(hours=2), end_time=START)

    with pytest.raises(ValueError, match="timezone-aware"):
        config(start_time=datetime(2025, 1, 1))
