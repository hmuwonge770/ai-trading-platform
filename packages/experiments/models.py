from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DatasetSplitConfig(BaseModel):
    """Chronological train/validation/test proportions for research datasets."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    train: Decimal = Field(default=Decimal("0.60"), gt=0, lt=1)
    validation: Decimal = Field(default=Decimal("0.20"), gt=0, lt=1)
    test: Decimal = Field(default=Decimal("0.20"), gt=0, lt=1)

    @model_validator(mode="after")
    def validate_total(self) -> DatasetSplitConfig:
        if self.train + self.validation + self.test != Decimal("1"):
            raise ValueError("train, validation, and test proportions must sum to 1")
        return self


class ExperimentConfig(BaseModel):
    """Immutable specification of one deterministic research experiment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    strategy_family: str = Field(min_length=1, max_length=100)
    strategy_config: dict[str, Any]
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: str = Field(min_length=1, max_length=16)
    start_time: datetime
    end_time: datetime
    initial_capital: Decimal = Field(gt=0)
    fee_rate: Decimal = Field(default=Decimal("0"), ge=0, lt=1)
    slippage_rate: Decimal = Field(default=Decimal("0"), ge=0, lt=1)
    dataset_split: DatasetSplitConfig = Field(default_factory=DatasetSplitConfig)
    engine_version: str = Field(default="stage5-v1", min_length=1, max_length=50)
    hypothesis: str | None = None
    generation: int = Field(default=0, ge=0)
    parent_experiment_id: str | None = None

    @field_validator("symbol", "timeframe")
    @classmethod
    def normalize_market_identifier(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_window(self) -> ExperimentConfig:
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            raise ValueError("start_time and end_time must be timezone-aware")
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self

    def dataset_config(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "splits": self.dataset_split.model_dump(mode="json"),
        }

    def parameters(self) -> dict[str, Any]:
        return {
            "strategy_family": self.strategy_family,
            "strategy_config": self.strategy_config,
            "initial_capital": str(self.initial_capital),
            "fee_rate": str(self.fee_rate),
            "slippage_rate": str(self.slippage_rate),
            "engine_version": self.engine_version,
            "hypothesis": self.hypothesis,
            "generation": self.generation,
            "parent_experiment_id": self.parent_experiment_id,
        }
