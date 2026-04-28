"""Async HTTP LLM client boundary."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from ..config import ModelConfig
from ..errors import ReasoningError


@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str
    raw: dict[str, Any]


class LLMClient:
    def __init__(self, config: ModelConfig, *, api_key: str = "") -> None:
        self._config = config
        self._api_key = api_key

    async def complete(self, *, system: str, user: str, timeout_seconds: float) -> LLMResponse:
        if not self._config.base_url:
            raise ReasoningError("LLM base_url is not configured")
        return await asyncio.to_thread(self._complete_sync, system, user, timeout_seconds)

    def _complete_sync(self, system: str, user: str, timeout_seconds: float) -> LLMResponse:
        url = self._config.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": self._config.model,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ReasoningError(f"LLM request failed: {exc}") from exc
        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ReasoningError("LLM returned invalid JSON") from exc
        text = extract_openai_text(data)
        return LLMResponse(text=text, raw=data)


def extract_openai_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                return str(message.get("content") or "").strip()
            return str(first.get("text") or "").strip()
    return str(data.get("text") or data.get("reply") or "").strip()

