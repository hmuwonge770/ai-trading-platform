from __future__ import annotations

from decimal import Decimal

import pytest

from packages.researcher.client import OpenAIResearchClient, ResearchModelError
from packages.researcher.models import ResearchContext, ResearchProposal
from packages.researcher.prompts import PROMPT_VERSION, build_research_prompt
from packages.researcher.researcher import AIResearcher


class FakeModel:
    def __init__(self, proposal: ResearchProposal) -> None:
        self.proposal = proposal
        self.prompt = ""

    def propose(self, user_prompt: str) -> ResearchProposal:
        self.prompt = user_prompt
        return self.proposal


def context() -> ResearchContext:
    return ResearchContext(
        objective="Find a falsifiable improvement to a simple trend-following strategy.",
        session_id="session-1",
        symbol="BTCUSDT",
        timeframe="1h",
        strategy_family="moving_average_crossover",
        current_strategy_config={"short_window": 3, "long_window": 5},
        parent_experiment_id="experiment-1",
        generation=0,
        experiment_budget_remaining=3,
        evidence={"train_return": "0.08", "validation_return": "0.02"},
    )


def proposal(**overrides) -> ResearchProposal:
    values = {
        "hypothesis": "A slightly longer short window may reduce noisy entries.",
        "rationale": "The current configuration has a stronger training result than validation result.",
        "expected_mechanism": "A longer short window should filter some short-lived crossovers.",
        "strategy_family": "moving_average_crossover",
        "strategy_config": {"short_window": 4, "long_window": 5},
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "parent_experiment_id": "experiment-1",
        "generation": 1,
        "experiment_plan": "Backtest only the proposed configuration on the predefined training partition.",
        "stopping_criterion": "Stop if the validation result does not improve or drawdown worsens materially.",
        "confidence": 0.55,
        "uncertainty": ["The evidence contains only a small number of summary metrics."],
    }
    values.update(overrides)
    return ResearchProposal(**values)


def test_researcher_returns_one_bounded_proposal() -> None:
    model = FakeModel(proposal())
    result = AIResearcher(model).propose_next_experiment(context())
    assert result.strategy_config == {"short_window": 4, "long_window": 5}
    assert PROMPT_VERSION in model.prompt
    assert "experiment-1" in model.prompt
    assert "OPENAI_API_KEY" not in model.prompt


def test_researcher_rejects_budget_exhaustion() -> None:
    model = FakeModel(proposal())
    exhausted = context().model_copy(update={"experiment_budget_remaining": 0})
    with pytest.raises(ValueError, match="no experiment budget"):
        AIResearcher(model).propose_next_experiment(exhausted)


def test_researcher_rejects_wrong_lineage_and_unchanged_config() -> None:
    model = FakeModel(proposal(parent_experiment_id="other"))
    with pytest.raises(ValueError, match="lineage"):
        AIResearcher(model).propose_next_experiment(context())

    unchanged = FakeModel(proposal(strategy_config=context().current_strategy_config))
    with pytest.raises(ValueError, match="meaningful"):
        AIResearcher(unchanged).propose_next_experiment(context())


def test_research_prompt_is_deterministic_and_serializable() -> None:
    first = build_research_prompt(context())
    second = build_research_prompt(context())
    assert first == second
    assert '"train_return":"0.08"' in first


class FakeResponse:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text


class FakeResponses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return FakeResponse(self.output_text)


class FakeOpenAI:
    def __init__(self, output_text: str) -> None:
        self.responses = FakeResponses(output_text)


def test_openai_adapter_validates_structured_output() -> None:
    fake = FakeOpenAI(proposal().model_dump_json())
    client = OpenAIResearchClient(
        api_key="test-key",
        model="gpt-5.6-luna",
        client=fake,
    )
    result = client.propose("research context")
    assert result.strategy_config["short_window"] == 4
    assert fake.responses.calls[0]["text"]["format"]["type"] == "json_schema"
    assert fake.responses.calls[0]["text"]["format"]["strict"] is True


def test_openai_adapter_rejects_invalid_structured_output() -> None:
    fake = FakeOpenAI('{"unexpected":"value"}')
    client = OpenAIResearchClient(api_key="test-key", model="gpt-5.6-luna", client=fake)
    with pytest.raises(ResearchModelError, match="invalid proposal"):
        client.propose("research context")


def test_openai_adapter_requires_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        OpenAIResearchClient(api_key="", model="gpt-5.6-luna")
