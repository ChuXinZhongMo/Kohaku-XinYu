from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_runtime.core.controller import Controller, ControllerConfig  # noqa: E402
from xinyu_runtime.core.events import EventType, TriggerEvent  # noqa: E402
from xinyu_runtime.llm.base import ChatResponse, LLMConfig, ToolSchema  # noqa: E402
from xinyu_runtime.llm.failover import (  # noqa: E402
    TinyKernelVisibleFailover,
    VisibleFailoverLLMProvider,
    wrap_llm_with_visible_failover,
)
from xinyu_runtime.parsing import TextEvent  # noqa: E402


class _RecoverablePrimaryError(RuntimeError):
    status_code = 401


class _QuotaPrimaryError(RuntimeError):
    status_code = 429


class _FailingPrimaryLLM:
    provider_name = "openai"
    provider_native_tools = frozenset()

    def __init__(self) -> None:
        self.config = LLMConfig(model="boom")
        self.prompt_cache_key: str | None = None
        self._last_tool_calls: list = []
        self._last_usage: dict[str, int] = {}

    @property
    def last_tool_calls(self) -> list:
        return self._last_tool_calls

    @property
    def last_usage(self) -> dict[str, int]:
        return self._last_usage

    async def chat(
        self,
        messages: list[dict],
        *,
        stream: bool = True,
        tools: list[ToolSchema] | None = None,
        provider_native_tools: list | None = None,
        **kwargs,
    ):
        raise _RecoverablePrimaryError("authentication failed")
        yield ""

    async def chat_complete(self, messages: list[dict], **kwargs) -> ChatResponse:
        raise _RecoverablePrimaryError("authentication failed")


class _ContextManagedPrimaryLLM(_FailingPrimaryLLM):
    def __init__(self) -> None:
        super().__init__()
        self.enter_count = 0
        self.exit_count = 0

    async def __aenter__(self) -> "_ContextManagedPrimaryLLM":
        self.enter_count += 1
        return self

    async def __aexit__(self, *args) -> None:
        self.exit_count += 1


def _failover_context(tmp_path: Path, *, text: str = "今晚我有点累") -> dict[str, object]:
    return {
        "enabled": True,
        "scope": "owner_private_chat",
        "source": "onebot_message_event",
        "turn_id": "turn-1",
        "session_key": "qq:private:1",
        "user_text": text,
        "trace_root": str(tmp_path),
        "context": {
            "recent_turns": [],
            "persona_state": "",
            "owner_profile": "",
            "runtime_state": "",
            "memory_recall": [],
        },
        "capabilities": {
            "codex_available": False,
            "external_api_available": False,
            "local_tools_available": True,
        },
        "constraints": {
            "max_reply_chars": 80,
            "allow_tool_request": False,
            "allow_memory_candidate": False,
        },
    }


def _tinykernel_post(endpoint: str, payload: dict[str, object], timeout_seconds: float) -> dict[str, object]:
    return {
        "ok": True,
        "mode": "reply",
        "reply_candidate": "本地兜底回来了。",
        "confidence": 0.82,
        "notes": ["tinykernel"],
    }


async def test_visible_failover_returns_local_reply_and_records_trace(tmp_path: Path) -> None:
    provider = wrap_llm_with_visible_failover(_FailingPrimaryLLM())
    provider._failover = TinyKernelVisibleFailover(post_fn=_tinykernel_post)

    controller = Controller(
        provider,
        ControllerConfig(
            system_prompt="You are a helpful assistant.",
            include_job_status=False,
            include_tools_list=False,
            max_messages=8,
            tool_format="bracket",
        ),
    )
    event = TriggerEvent(
        type=EventType.USER_INPUT,
        content="今晚我有点累",
        context={"llm_failover": _failover_context(tmp_path)},
    )
    await controller.push_event(event)

    chunks: list[str] = []
    async for parse_event in controller.run_once():
        if isinstance(parse_event, TextEvent):
            chunks.append(parse_event.text)

    reply = "".join(chunks)
    trace_path = tmp_path / "runtime/tinykernel_failover_trace.jsonl"

    assert "本地兜底回来了" in reply
    assert trace_path.exists()
    trace_text = trace_path.read_text(encoding="utf-8")
    assert "今晚我有点累" not in trace_text


async def test_visible_failover_recovers_from_quota_limit(tmp_path: Path) -> None:
    class _QuotaFailingPrimaryLLM(_FailingPrimaryLLM):
        async def chat(self, messages: list[dict], *, stream: bool = True, tools: list[ToolSchema] | None = None, provider_native_tools: list | None = None, **kwargs):  # noqa: ANN001
            raise _QuotaPrimaryError("insufficient quota")
            yield ""

        async def chat_complete(self, messages: list[dict], **kwargs) -> ChatResponse:  # noqa: ANN001
            raise _QuotaPrimaryError("insufficient quota")

    provider = wrap_llm_with_visible_failover(_QuotaFailingPrimaryLLM())
    provider._failover = TinyKernelVisibleFailover(post_fn=_tinykernel_post)

    controller = Controller(
        provider,
        ControllerConfig(
            system_prompt="You are a helpful assistant.",
            include_job_status=False,
            include_tools_list=False,
            max_messages=8,
            tool_format="bracket",
        ),
    )
    event = TriggerEvent(
        type=EventType.USER_INPUT,
        content="额度到了吗",
        context={"llm_failover": _failover_context(tmp_path, text="额度到了吗")},
    )
    await controller.push_event(event)

    chunks: list[str] = []
    async for parse_event in controller.run_once():
        if isinstance(parse_event, TextEvent):
            chunks.append(parse_event.text)

    reply = "".join(chunks)
    assert "本地兜底回来了" in reply


async def test_visible_failover_skips_tool_turns() -> None:
    provider = wrap_llm_with_visible_failover(_FailingPrimaryLLM())
    provider._xinyu_llm_failover_context = _failover_context(Path.cwd())

    with pytest.raises(_RecoverablePrimaryError):
        async for _ in provider.chat(
            [{"role": "user", "content": "帮我读一下这个项目"}],
            tools=[ToolSchema(name="read", description="read")],
        ):
            pass


async def test_visible_failover_preserves_async_context_manager() -> None:
    primary = _ContextManagedPrimaryLLM()
    provider = wrap_llm_with_visible_failover(primary)

    async with provider as wrapped:
        assert wrapped is provider

    assert primary.enter_count == 1
    assert primary.exit_count == 1
