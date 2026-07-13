from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The core runtime transitively imports the TUI stack (textual); in a minimal env
# without it, skip the whole module instead of erroring at collection.
pytest.importorskip("textual")

from xinyu_runtime.core.controller import Controller, ControllerConfig  # noqa: E402
from xinyu_runtime.core.events import EventType, TriggerEvent  # noqa: E402
from xinyu_runtime.llm.base import ChatResponse, LLMConfig, ToolSchema  # noqa: E402
from xinyu_runtime.llm.failover import (  # noqa: E402
    TinyKernelVisibleFailover,
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


def _tinykernel_stale_plan_post(endpoint: str, payload: dict[str, object], timeout_seconds: float) -> dict[str, object]:
    return {
        "ok": True,
        "mode": "reply",
        "reply_candidate": "我明白。先按最小可运行版本推进，不直接动主链路。",
        "confidence": 0.62,
        "notes": ["compose_shadow", "shadow_only", "compose_fallback_persona"],
    }


def _tinykernel_bare_ack_post(endpoint: str, payload: dict[str, object], timeout_seconds: float) -> dict[str, object]:
    return {
        "ok": True,
        "mode": "reply",
        "reply_candidate": "嗯。",
        "confidence": 0.62,
        "notes": ["compose_shadow", "shadow_only", "compose_fallback_persona"],
    }


def _tinykernel_default_reply_post(
    endpoint: str,
    payload: dict[str, object],
    timeout_seconds: float,
) -> dict[str, object]:
    return {
        "ok": True,
        "mode": "reply",
        "reply_candidate": "我明白。",
        "confidence": 0.55,
        "notes": ["compose_shadow", "default_reply"],
    }


class _TinyKernelRetryPost:
    def __init__(self, first_post, retry_reply: str) -> None:
        self.first_post = first_post
        self.retry_reply = retry_reply
        self.calls: list[dict[str, object]] = []

    def __call__(self, endpoint: str, payload: dict[str, object], timeout_seconds: float) -> dict[str, object]:
        self.calls.append(payload)
        if len(self.calls) == 1:
            return self.first_post(endpoint, payload, timeout_seconds)
        assert isinstance(payload.get("quality_retry"), dict)
        return {
            "ok": True,
            "mode": "reply",
            "reply_candidate": self.retry_reply,
            "confidence": 0.71,
            "notes": ["compose_shadow", "quality_retry"],
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


async def test_visible_failover_replaces_stale_project_reply_for_life_chat(tmp_path: Path) -> None:
    retry_post = _TinyKernelRetryPost(
        _tinykernel_stale_plan_post,
        "收住了。今晚不把话硬往下推。",
    )
    provider = wrap_llm_with_visible_failover(_FailingPrimaryLLM())
    provider._failover = TinyKernelVisibleFailover(post_fn=retry_post)

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
    user_text = "感觉你今天没什么精神，我就不吵你了，早点睡。"
    event = TriggerEvent(
        type=EventType.USER_INPUT,
        content=user_text,
        context={"llm_failover": _failover_context(tmp_path, text=user_text)},
    )
    await controller.push_event(event)

    chunks: list[str] = []
    async for parse_event in controller.run_once():
        if isinstance(parse_event, TextEvent):
            chunks.append(parse_event.text)

    reply = "".join(chunks)
    assert "主链路" not in reply
    assert "最小可运行" not in reply
    assert reply == "收住了。今晚不把话硬往下推。"
    assert len(retry_post.calls) == 2
    trace_text = (tmp_path / "runtime/tinykernel_failover_trace.jsonl").read_text(encoding="utf-8")
    assert "tinykernel_stale_plan_reply_replaced" in trace_text
    assert "tinykernel_stale_plan_reply_replaced_retry_accepted" in trace_text


async def test_visible_failover_keeps_project_reply_for_technical_chat(tmp_path: Path) -> None:
    provider = wrap_llm_with_visible_failover(_FailingPrimaryLLM())
    provider._failover = TinyKernelVisibleFailover(post_fn=_tinykernel_stale_plan_post)

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
    user_text = "继续修主链路代码"
    event = TriggerEvent(
        type=EventType.USER_INPUT,
        content=user_text,
        context={"llm_failover": _failover_context(tmp_path, text=user_text)},
    )
    await controller.push_event(event)

    chunks: list[str] = []
    async for parse_event in controller.run_once():
        if isinstance(parse_event, TextEvent):
            chunks.append(parse_event.text)

    reply = "".join(chunks)
    assert "主链路" in reply
    assert "最小可运行" in reply
    trace_text = (tmp_path / "runtime/tinykernel_failover_trace.jsonl").read_text(encoding="utf-8")
    assert "tinykernel_stale_plan_reply_replaced" not in trace_text


async def test_visible_failover_replaces_bare_ack_for_sleep_question(tmp_path: Path) -> None:
    retry_post = _TinyKernelRetryPost(
        _tinykernel_bare_ack_post,
        "困了就先别撑着聊。",
    )
    provider = wrap_llm_with_visible_failover(_FailingPrimaryLLM())
    provider._failover = TinyKernelVisibleFailover(post_fn=retry_post)

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
    user_text = "困了？"
    event = TriggerEvent(
        type=EventType.USER_INPUT,
        content=user_text,
        context={"llm_failover": _failover_context(tmp_path, text=user_text)},
    )
    await controller.push_event(event)

    chunks: list[str] = []
    async for parse_event in controller.run_once():
        if isinstance(parse_event, TextEvent):
            chunks.append(parse_event.text)

    reply = "".join(chunks)
    assert reply != "嗯。"
    assert reply == "困了就先别撑着聊。"
    assert len(retry_post.calls) == 2


async def test_visible_failover_replaces_bare_ack_for_short_sigh(tmp_path: Path) -> None:
    retry_post = _TinyKernelRetryPost(
        _tinykernel_bare_ack_post,
        "在，刚才只冒了个音。",
    )
    provider = wrap_llm_with_visible_failover(_FailingPrimaryLLM())
    provider._failover = TinyKernelVisibleFailover(post_fn=retry_post)

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
    user_text = "唉"
    event = TriggerEvent(
        type=EventType.USER_INPUT,
        content=user_text,
        context={"llm_failover": _failover_context(tmp_path, text=user_text)},
    )
    await controller.push_event(event)

    chunks: list[str] = []
    async for parse_event in controller.run_once():
        if isinstance(parse_event, TextEvent):
            chunks.append(parse_event.text)

    reply = "".join(chunks)
    assert reply == "在，刚才只冒了个音。"
    assert len(retry_post.calls) == 2
    trace_text = (tmp_path / "runtime/tinykernel_failover_trace.jsonl").read_text(encoding="utf-8")
    assert "tinykernel_bare_ack_replaced" in trace_text
    assert "tinykernel_bare_ack_replaced_retry_accepted" in trace_text


async def test_visible_failover_replaces_default_reply_for_life_chat(tmp_path: Path) -> None:
    retry_post = _TinyKernelRetryPost(
        _tinykernel_default_reply_post,
        "今晚确实有点低，我不用那种应声糊你。",
    )
    provider = wrap_llm_with_visible_failover(_FailingPrimaryLLM())
    provider._failover = TinyKernelVisibleFailover(post_fn=retry_post)

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
    user_text = "今晚我有点累"
    event = TriggerEvent(
        type=EventType.USER_INPUT,
        content=user_text,
        context={"llm_failover": _failover_context(tmp_path, text=user_text)},
    )
    await controller.push_event(event)

    chunks: list[str] = []
    async for parse_event in controller.run_once():
        if isinstance(parse_event, TextEvent):
            chunks.append(parse_event.text)

    reply = "".join(chunks)
    assert reply != "我明白。"
    assert reply == "今晚确实有点低，我不用那种应声糊你。"
    assert len(retry_post.calls) == 2
    trace_text = (tmp_path / "runtime/tinykernel_failover_trace.jsonl").read_text(encoding="utf-8")
    assert "tinykernel_default_reply_replaced" in trace_text
    assert "tinykernel_default_reply_replaced_retry_accepted" in trace_text


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
