from __future__ import annotations

import asyncio
import json

from xinyu_llm_api import anthropic_messages_endpoint, anthropic_payload_from_messages
from xinyu_v1.config import ModelConfig
from xinyu_v1.reasoning import llm_client
from xinyu_v1.reasoning.llm_client import LLMClient


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def __enter__(self):  # noqa: ANN204
        return self

    def __exit__(self, *args) -> None:  # noqa: ANN002
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_anthropic_messages_endpoint_accepts_root_or_v1_base() -> None:
    assert anthropic_messages_endpoint("https://muyuan.do") == "https://muyuan.do/v1/messages"
    assert anthropic_messages_endpoint("https://muyuan.do/v1") == "https://muyuan.do/v1/messages"


def test_anthropic_payload_splits_system_from_dialogue() -> None:
    payload = anthropic_payload_from_messages(
        [
            {"role": "system", "content": "rules"},
            {"role": "user", "content": "ping"},
        ],
        model="claude-opus-4-8",
        temperature=0.1,
        max_tokens=8,
    )

    assert payload["system"] == "rules"
    assert payload["messages"] == [{"role": "user", "content": "ping"}]


def test_llm_client_message_provider_uses_anthropic_messages(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response({"content": [{"type": "text", "text": "ok"}]})

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    client = LLMClient(
        ModelConfig(
            provider="message",
            model="claude-opus-4-8",
            base_url="https://muyuan.do",
            temperature=0.2,
            max_tokens=16,
        ),
        api_key="test-key",
    )
    response = asyncio.run(client.complete(system="Return JSON", user="ping", timeout_seconds=3))

    headers = captured["headers"]
    body = captured["body"]
    assert response.text == "ok"
    assert captured["url"] == "https://muyuan.do/v1/messages"
    assert captured["timeout"] == 3
    assert isinstance(headers, dict)
    assert headers["anthropic-version"] == "2023-06-01"
    assert headers["x-api-key"] == "test-key"
    assert isinstance(body, dict)
    assert body["system"] == "Return JSON"
    assert body["messages"] == [{"role": "user", "content": "ping"}]


def test_llm_client_openai_provider_keeps_chat_completions(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):  # noqa: ANN001
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(llm_client.urllib.request, "urlopen", fake_urlopen)

    client = LLMClient(
        ModelConfig(
            provider="openai",
            model="mimo-v2.5",
            base_url="https://example.test/v1",
        ),
        api_key="test-key",
    )
    response = asyncio.run(client.complete(system="Return JSON", user="ping", timeout_seconds=3))

    body = captured["body"]
    assert response.text == "ok"
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert isinstance(body, dict)
    assert body["messages"][0] == {"role": "system", "content": "Return JSON"}
