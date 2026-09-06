from __future__ import annotations

from typing import Protocol

from packages.researcher.models import ResearchContext, ResearchProposal
from packages.researcher.prompts import build_research_prompt


class ResearchModel(Protocol):
    def propose(self, user_prompt: str) -> ResearchProposal:
        ...


class AIResearcher:
    """Generate one bounded research proposal without executing it."""

    def __init__(self, model: ResearchModel) -> None:
        self._model = model

    def propose_next_experiment(self, context: ResearchContext) -> ResearchProposal:
        if context.experiment_budget_remaining <= 0:
            raise ValueError("no experiment budget remains")

        proposal = self._model.propose(build_research_prompt(context))
        self._validate_proposal(context, proposal)
        return proposal

    @staticmethod
    def _validate_proposal(
        context: ResearchContext,
        proposal: ResearchProposal,
    ) -> None:
        if proposal.strategy_family != context.strategy_family:
            raise ValueError("researcher cannot change strategy family in Stage 7")
        if proposal.symbol != context.symbol or proposal.timeframe != context.timeframe:
            raise ValueError("researcher cannot change market scope in Stage 7")
        if proposal.parent_experiment_id != context.parent_experiment_id:
            raise ValueError("proposal lineage does not match research context")
        if proposal.generation != context.generation + 1:
            raise ValueError("proposal generation must advance exactly one step")
        if proposal.strategy_config == context.current_strategy_config:
            raise ValueError("proposal must make a meaningful strategy configuration change")
