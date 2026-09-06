from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from apps.api.schemas import ExperimentCreate, ResearchSessionCreate
from packages.experiments.models import DatasetSplitConfig, ExperimentConfig


def test_research_session_request_rejects_empty_name():
    with pytest.raises(ValidationError):
        ResearchSessionCreate(name="", objective="test")


def test_experiment_request_uses_immutable_research_config():
    request = ExperimentCreate(
        strategy_family="moving_average",
        strategy_config={"short_window": 10, "long_window": 30},
        symbol="btcusdt",
        timeframe="1h",
        start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2025, 2, 1, tzinfo=timezone.utc),
        initial_capital=Decimal("10000"),
    )

    config = ExperimentConfig(
        session_id=str(uuid.uuid4()),
        strategy_family=request.strategy_family,
        strategy_config=request.strategy_config,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_time=request.start_time,
        end_time=request.end_time,
        initial_capital=request.initial_capital,
        fee_rate=request.fee_rate,
        slippage_rate=request.slippage_rate,
        dataset_split=request.dataset_split,
        engine_version=request.engine_version,
        hypothesis=request.hypothesis,
        generation=request.generation,
        parent_experiment_id=(
            str(request.parent_experiment_id) if request.parent_experiment_id else None
        ),
    )

    assert config.symbol == "BTCUSDT"
    assert config.timeframe == "1H"
    assert config.dataset_split == DatasetSplitConfig()
    with pytest.raises(ValidationError):
        config.strategy_family = "other"  # type: ignore[misc]


def test_experiment_request_rejects_naive_datetimes():
    with pytest.raises(ValidationError, match="timezone-aware"):
        ExperimentCreate(
            strategy_family="moving_average",
            strategy_config={"short_window": 10, "long_window": 30},
            symbol="BTCUSDT",
            timeframe="1h",
            start_time=datetime(2025, 1, 1),
            end_time=datetime(2025, 2, 1, tzinfo=timezone.utc),
            initial_capital=Decimal("10000"),
        )


def test_dataset_split_must_sum_to_one():
    with pytest.raises(ValidationError, match="sum to 1"):
        DatasetSplitConfig(train=Decimal("0.70"), validation=Decimal("0.20"), test=Decimal("0.20"))
