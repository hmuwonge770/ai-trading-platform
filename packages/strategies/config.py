from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrategyConfig(BaseModel):
    """Base configuration for a structured, non-executable strategy."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class MovingAverageCrossoverConfig(StrategyConfig):
    """Configuration for a simple moving-average crossover strategy."""

    short_window: int = Field(gt=0)
    long_window: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_window_order(self) -> MovingAverageCrossoverConfig:
        if self.short_window >= self.long_window:
            raise ValueError("short_window must be smaller than long_window")
        return self
