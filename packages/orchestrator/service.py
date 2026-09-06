from __future__ import annotations

from collections.abc import Callable

from packages.orchestrator.models import OrchestrationConfig, OrchestrationResult
from packages.researcher.models import ResearchContext, ResearchProposal
from packages.researcher.researcher import AIResearcher


class ExperimentOrchestrator:
    """Run a bounded research-proposal loop without executing experiments."""

    def __init__(self, researcher: AIResearcher, config: OrchestrationConfig | None = None) -> None:
        self.researcher = researcher
        self.config = config or OrchestrationConfig()

    def run(
        self,
        context: ResearchContext,
        *,
        on_proposal: Callable[[ResearchProposal], None] | None = None,
    ) -> OrchestrationResult:
        proposals: list[str] = []
        current = context

        for _ in range(self.config.max_experiments):
            if current.experiment_budget_remaining <= 0:
                return self._result(proposals, "experiment_budget_exhausted")
            if current.generation >= self.config.max_generations:
                return self._result(proposals, "generation_limit_reached")

            proposal = self.researcher.propose_next_experiment(current)
            if on_proposal is not None:
                on_proposal(proposal)

            proposals.append(f"generation-{proposal.generation}")
            current = current.model_copy(
                update={
                    "current_strategy_config": proposal.strategy_config,
                    "parent_experiment_id": proposal.parent_experiment_id,
                    "generation": proposal.generation,
                    "experiment_budget_remaining": current.experiment_budget_remaining - 1,
                }
            )

        return self._result(proposals, "experiment_limit_reached")

    @staticmethod
    def _result(proposals: list[str], reason: str) -> OrchestrationResult:
        return OrchestrationResult(
            experiments_created=len(proposals),
            generations_completed=len(proposals),
            stopped_reason=reason,
            proposal_ids=tuple(proposals),
        )
