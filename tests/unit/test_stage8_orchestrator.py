from packages.orchestrator.models import OrchestrationConfig
from packages.orchestrator.service import ExperimentOrchestrator
from packages.researcher.models import ResearchContext, ResearchProposal


class FakeResearcher:
    def __init__(self):
        self.calls = 0

    def propose_next_experiment(self, context):
        self.calls += 1
        return ResearchProposal(
            hypothesis="A small parameter change may improve robustness.",
            rationale="The current evidence leaves room for a focused follow-up.",
            expected_mechanism="The change may reduce noisy signals.",
            strategy_family=context.strategy_family,
            strategy_config={"short_window": 4, "long_window": 5},
            symbol=context.symbol,
            timeframe=context.timeframe,
            parent_experiment_id=context.parent_experiment_id,
            generation=context.generation + 1,
            experiment_plan="Run the proposed configuration on the predefined training partition.",
            stopping_criterion="Stop if validation evidence does not improve.",
            confidence=0.5,
            uncertainty=["Limited evidence"],
        )


def context():
    return ResearchContext(
        objective="Improve trend following.",
        session_id="session-1",
        symbol="BTCUSDT",
        timeframe="1h",
        strategy_family="moving_average_crossover",
        current_strategy_config={"short_window": 3, "long_window": 5},
        parent_experiment_id="experiment-1",
        generation=0,
        experiment_budget_remaining=2,
    )


def test_orchestrator_respects_budget_and_emits_proposals():
    researcher = FakeResearcher()
    result = ExperimentOrchestrator(researcher, OrchestrationConfig(max_experiments=5)).run(context())
    assert result.experiments_created == 2
    assert result.stopped_reason == "experiment_budget_exhausted"
    assert researcher.calls == 2


def test_orchestrator_respects_generation_limit():
    researcher = FakeResearcher()
    result = ExperimentOrchestrator(
        researcher, OrchestrationConfig(max_experiments=5, max_generations=1)
    ).run(context())
    assert result.experiments_created == 1
    assert result.stopped_reason == "generation_limit_reached"
