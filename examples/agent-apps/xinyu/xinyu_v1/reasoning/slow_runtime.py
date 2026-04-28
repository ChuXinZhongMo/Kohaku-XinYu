"""Slow reasoning runtime."""

from __future__ import annotations

import os

from ..config import ModelConfig
from ..types import ResourceUsage, TokenBudget
from .llm_client import LLMClient
from .models import ReasoningRequest, ReasoningResult
from .prompt_builder import PromptBuilder


class SlowReasoningRuntime:
    def __init__(
        self,
        model_config: ModelConfig,
        *,
        llm_client: LLMClient | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        api_key = os.environ.get(model_config.api_key_env, "")
        self._client = llm_client or LLMClient(model_config, api_key=api_key)
        self._prompt_builder = prompt_builder or PromptBuilder(TokenBudget(total=model_config.max_tokens).validate())

    async def run(self, request: ReasoningRequest, *, timeout_seconds: float) -> ReasoningResult:
        bundle = self._prompt_builder.build(request)
        response = await self._client.complete(system=bundle.system, user=bundle.user, timeout_seconds=timeout_seconds)
        return ReasoningResult(
            draft=response.text,
            memory_changed=None,
            notes=(*bundle.notes, "llm_complete"),
            usage=ResourceUsage(model_calls=1),
        )

