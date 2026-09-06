from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchContext(BaseModel):
    """Non-secret evidence supplied to the AI research layer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    objective: str = Field(min_length=1, max_length=4000)
    session_id: str = Field(min_length=1, max_length=100)
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: str = Field(min_length=1, max_length=16)
    strategy_family: str = Field(min_length=1, max_length=100)
    current_strategy_config: dict[str, Any] = Field(default_factory=dict)
    parent_experiment_id: str | None = None
    generation: int = Field(default=0, ge=0)
    experiment_budget_remaining: int = Field(default=1, ge=0)
    evidence: dict[str, Any] = Field(default_factory=dict)


class ResearchProposal(BaseModel):
    """A structured research proposal that can be handed to Stage 8."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    hypothesis: str = Field(min_length=10, max_length=2000)
    rationale: str = Field(min_length=10, max_length=4000)
    expected_mechanism: str = Field(min_length=10, max_length=2000)
    strategy_family: str = Field(min_length=1, max_length=100)
    strategy_config: dict[str, Any] = Field(default_factory=dict)
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: str = Field(min_length=1, max_length=16)
    parent_experiment_id: str | None = None
    generation: int = Field(default=0, ge=0)
    experiment_plan: str = Field(min_length=10, max_length=3000)
    stopping_criterion: str = Field(min_length=10, max_length=2000)
    confidence: float = Field(ge=0, le=1)
    uncertainty: list[str] = Field(default_factory=list, max_length=10)

    @property
    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible proposal for persistence or messaging."""
        return self.model_dump(mode="json")
