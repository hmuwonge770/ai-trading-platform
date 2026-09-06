from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from packages.database.models import ExperimentStatus, ResearchSessionStatus
from packages.experiments.models import DatasetSplitConfig


class ResearchSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)


class ResearchSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    objective: str
    status: ResearchSessionStatus
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ExperimentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    parent_experiment_id: uuid.UUID | None = None


class ExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    strategy_version_id: uuid.UUID | None
    status: ExperimentStatus
    parameters: dict[str, Any]
    dataset_config: dict[str, Any]
    experiment_fingerprint: str
    engine_version: str
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class CandleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    quote_volume: Decimal
    trade_count: int
