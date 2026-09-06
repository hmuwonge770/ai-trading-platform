from __future__ import annotations

import json

from packages.researcher.models import ResearchContext

PROMPT_VERSION = "stage7-v1"

SYSTEM_PROMPT = """You are a quantitative research scientist inside a research-first trading platform.

Your job is to propose the next falsifiable experiment, not to trade.

Hard boundaries:
- Never propose orders, execution instructions, exchange credentials, or live-trading actions.
- Work only with the supplied research context and evidence.
- Preserve chronological train/validation/final-test isolation.
- Make the smallest meaningful change from the current strategy configuration.
- Prefer one informative experiment over broad parameter sweeps.
- Do not claim evidence that is not present in the supplied context.
- If evidence is weak or insufficient, say so in uncertainty and reduce confidence.
- The proposal must be suitable for deterministic backtesting by a separate engine.
- The final test set is sealed and must not be used to choose parameters.

Return exactly the requested structured research proposal.
"""


def build_research_prompt(context: ResearchContext) -> str:
    """Build a deterministic prompt from non-secret research data."""
    payload = context.model_dump(mode="json")
    return (
        f"Research prompt version: {PROMPT_VERSION}\n\n"
        "Analyze the following research context and propose exactly one next experiment.\n\n"
        f"{json.dumps(payload, sort_keys=True, separators=(',', ':'))}"
    )


def proposal_json_schema() -> dict:
    """JSON Schema enforced at the model boundary."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "hypothesis": {"type": "string"},
            "rationale": {"type": "string"},
            "expected_mechanism": {"type": "string"},
            "strategy_family": {"type": "string"},
            "strategy_config": {"type": "object"},
            "symbol": {"type": "string"},
            "timeframe": {"type": "string"},
            "parent_experiment_id": {"type": ["string", "null"]},
            "generation": {"type": "integer", "minimum": 0},
            "experiment_plan": {"type": "string"},
            "stopping_criterion": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "uncertainty": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 10,
            },
        },
        "required": [
            "hypothesis",
            "rationale",
            "expected_mechanism",
            "strategy_family",
            "strategy_config",
            "symbol",
            "timeframe",
            "parent_experiment_id",
            "generation",
            "experiment_plan",
            "stopping_criterion",
            "confidence",
            "uncertainty",
        ],
    }
