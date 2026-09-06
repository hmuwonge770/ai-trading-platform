from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class OrchestrationConfig(BaseModel):
    """Hard limits for one research orchestration run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_experiments: int = Field(default=5, ge=1, le=100)
    max_generations: int = Field(default=5, ge=1, le=100)


class OrchestrationResult(BaseModel):
    """Deterministic summary of an orchestration run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiments_created: int = Field(ge=0)
    generations_completed: int = Field(ge=0)
    stopped_reason: str = Field(min_length=1)
    proposal_ids: tuple[str, ...] = ()
