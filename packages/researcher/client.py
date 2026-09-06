from __future__ import annotations

from typing import Any

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError

from packages.researcher.models import ResearchProposal
from packages.researcher.prompts import SYSTEM_PROMPT, proposal_json_schema


class ResearchModelError(RuntimeError):
    """Raised when the research model cannot produce a valid proposal."""


class OpenAIResearchClient:
    """Small OpenAI Responses API adapter with no trading capabilities."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout: float = 30.0,
        max_retries: int = 2,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.model = model
        self.max_retries = max_retries
        self._client = client or OpenAI(api_key=api_key, timeout=timeout, max_retries=0)

    def propose(self, user_prompt: str) -> ResearchProposal:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self._client.responses.create(
                    model=self.model,
                    input=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "research_proposal",
                            "strict": True,
                            "schema": proposal_json_schema(),
                        }
                    },
                )
                output = response.output_text
                if not output:
                    raise ResearchModelError("research model returned empty output")
                try:
                    return ResearchProposal.model_validate_json(output)
                except ValueError as exc:
                    raise ResearchModelError("research model returned invalid proposal") from exc
            except (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError) as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break

        raise ResearchModelError("research model request failed") from last_error
