"""Async HTTP LLM client boundary."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from xinyu_llm_api import (
    anthropic_headers,
    anthropic_messages_endpoint,
    anthropic_payload_from_messages,
    extract_api_error_message,
    extract_anthropic_text,
    extract_openai_text,
    is_anthropic_messages_provider,
    openai_headers,
)

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

    async def complete(
        self,
        *,
        system: str,
        user: str,
        timeout_seconds: float,
        history: Sequence[Mapping[str, str]] = (),
    ) -> LLMResponse:
        if not self._config.base_url:
            raise ReasoningError("LLM base_url is not configured")
        return await asyncio.to_thread(self._complete_sync, system, user, timeout_seconds, tuple(history))

    def _complete_sync(
        self,
        system: str,
        user: str,
        timeout_seconds: float,
        history: Sequence[Mapping[str, str]],
    ) -> LLMResponse:
        if is_anthropic_messages_provider(self._config.provider):
            return self._complete_anthropic_sync(system, user, timeout_seconds, history)
        return self._complete_openai_sync(system, user, timeout_seconds, history)

    def _complete_openai_sync(
        self,
        system: str,
        user: str,
        timeout_seconds: float,
        history: Sequence[Mapping[str, str]],
    ) -> LLMResponse:
        url = self._config.base_url.rstrip("/") + "/chat/completions"
        messages = [{"role": "system", "content": system}, *_conversation_messages(history, user)]
        payload = {
            "model": self._config.model,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "messages": messages,
        }
        data = post_json(url, payload, openai_headers(self._api_key), timeout_seconds)
        text = extract_openai_text(data)
        return LLMResponse(text=text, raw=data)

    def _complete_anthropic_sync(
        self,
        system: str,
        user: str,
        timeout_seconds: float,
        history: Sequence[Mapping[str, str]],
    ) -> LLMResponse:
        messages = [{"role": "system", "content": system}, *_conversation_messages(history, user)]
        payload = anthropic_payload_from_messages(
            messages,
            model=self._config.model,
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
        )
        data = post_json(
            anthropic_messages_endpoint(self._config.base_url),
            payload,
            anthropic_headers(self._api_key),
            timeout_seconds,
        )
        text = extract_anthropic_text(data)
        return LLMResponse(text=text, raw=data)


def _conversation_messages(history: Sequence[Mapping[str, str]], user: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for message in history:
        role = str(message.get("role") or "").strip()
        content = str(message.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user})
    return messages


def post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        detail = http_error_detail(body) or exc.reason
        raise ReasoningError(f"LLM request failed: HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ReasoningError(f"LLM request failed: {exc}") from exc
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ReasoningError("LLM returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise ReasoningError("LLM returned non-object JSON")
    return data


def http_error_detail(body: str) -> str:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body.replace("\n", " ").strip()[:220]
    if not isinstance(data, dict):
        return ""
    return extract_api_error_message(data)[:220]
