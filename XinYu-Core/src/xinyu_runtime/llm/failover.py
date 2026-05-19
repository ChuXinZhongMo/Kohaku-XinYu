"""Visible local failover for owner-private chat turns.

The wrapper is inert unless a controller turn supplies an explicit
``llm_failover`` context. This keeps generic agents, tool turns, Codex routes,
and proactive flows on the primary provider.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Iterator

from xinyu_runtime.llm.base import ChatResponse, LLMConfig, NativeToolCall, ToolSchema
from xinyu_runtime.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TINYKERNEL_FAILOVER_ENDPOINT = "http://127.0.0.1:8877/compose_shadow"
FAILOVER_ENABLED_ENV = "XINYU_TINYKERNEL_FAILOVER_ENABLED"
FAILOVER_ENDPOINT_ENV = "XINYU_TINYKERNEL_FAILOVER_ENDPOINT"
FAILOVER_TIMEOUT_ENV = "XINYU_TINYKERNEL_FAILOVER_TIMEOUT_SECONDS"
TRACE_REL = Path("runtime/tinykernel_failover_trace.jsonl")

PostFn = Callable[[str, dict[str, Any], float], dict[str, Any]]

_RECOVERABLE_STATUS_CODES = {401, 402, 408, 429, 500, 502, 503, 504}
_RECOVERABLE_ERROR_NAME_PARTS = (
    "authentication",
    "rate_limit",
    "ratelimit",
    "timeout",
    "connection",
    "network",
    "apiresponse",
    "apiconnection",
)
_RECOVERABLE_MESSAGE_PARTS = (
    "insufficient_quota",
    "quota",
    "rate limit",
    "rate_limit",
    "api key",
    "unauthorized",
    "authentication",
    "timed out",
    "timeout",
    "connection",
    "network",
)


def wrap_llm_with_visible_failover(provider: Any) -> Any:
    """Wrap an LLM provider with TinyKernel failover support."""
    if isinstance(provider, VisibleFailoverLLMProvider):
        return provider
    return VisibleFailoverLLMProvider(provider)


@contextmanager
def provider_failover_context(provider: Any, context: dict[str, Any] | None) -> Iterator[None]:
    """Temporarily attach per-turn failover context to a provider."""
    previous = getattr(provider, "_xinyu_llm_failover_context", None)
    if context:
        setattr(provider, "_xinyu_llm_failover_context", context)
    else:
        try:
            delattr(provider, "_xinyu_llm_failover_context")
        except AttributeError:
            pass
    try:
        yield
    finally:
        if previous is None:
            try:
                delattr(provider, "_xinyu_llm_failover_context")
            except AttributeError:
                pass
        else:
            setattr(provider, "_xinyu_llm_failover_context", previous)


def failover_context_from_events(events: list[Any]) -> dict[str, Any] | None:
    """Return the last enabled ``llm_failover`` context from turn events."""
    for event in reversed(events):
        event_context = getattr(event, "context", None)
        if not isinstance(event_context, dict):
            continue
        value = event_context.get("llm_failover")
        if isinstance(value, dict) and value.get("enabled"):
            return value
    return None


def is_recoverable_llm_error(exc: BaseException) -> bool:
    """True when an LLM exception is suitable for local visible failover."""
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if _is_recoverable_single_error(current):
            return True
        current = current.__cause__ or current.__context__
    return False


def _is_recoverable_single_error(exc: BaseException) -> bool:
    status = _status_code(exc)
    if status in _RECOVERABLE_STATUS_CODES:
        return True
    if isinstance(exc, (TimeoutError, ConnectionError, OSError, urllib.error.URLError)):
        return True
    name = type(exc).__name__.lower()
    if any(part in name for part in _RECOVERABLE_ERROR_NAME_PARTS):
        return True
    message = str(exc).lower()
    return any(part in message for part in _RECOVERABLE_MESSAGE_PARTS)


def _status_code(exc: BaseException) -> int | None:
    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            return int(getattr(response, "status_code", None))
        except (TypeError, ValueError):
            return None
    return None


def _env_flag_enabled(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _timeout_seconds() -> float:
    try:
        value = float(os.environ.get(FAILOVER_TIMEOUT_ENV, "2.0"))
    except ValueError:
        value = 2.0
    return max(0.1, min(10.0, value))


def _post_json(endpoint: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8", errors="replace")
    value = json.loads(body)
    return value if isinstance(value, dict) else {}


class TinyKernelVisibleFailover:
    """Client for TinyKernel's local reply candidate endpoints."""

    def __init__(self, post_fn: PostFn | None = None):
        self._post_fn = post_fn or _post_json

    async def complete(self, context: dict[str, Any], *, primary_error: BaseException) -> str:
        if not _env_flag_enabled(FAILOVER_ENABLED_ENV, default=True):
            raise primary_error
        endpoint = str(
            context.get("endpoint")
            or os.environ.get(FAILOVER_ENDPOINT_ENV)
            or DEFAULT_TINYKERNEL_FAILOVER_ENDPOINT
        ).strip()
        if not endpoint:
            raise primary_error
        payload = _build_tinykernel_payload(context)
        started = time.perf_counter()
        response: dict[str, Any] = {}
        error = ""
        try:
            response = await asyncio.to_thread(self._post_fn, endpoint, payload, _timeout_seconds())
            reply = _visible_reply_from_tinykernel(response, context)
            if not reply:
                error = "empty_tinykernel_reply"
                raise primary_error
            return reply
        except Exception as exc:
            error = error or f"{type(exc).__name__}:{exc}"
            if exc is primary_error:
                raise
            raise primary_error from exc
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            _record_failover_trace(
                context,
                response=response,
                ok=bool(response and not error),
                error=error,
                elapsed_ms=elapsed_ms,
                primary_error=primary_error,
            )


def _build_tinykernel_payload(context: dict[str, Any]) -> dict[str, Any]:
    constraints = context.get("constraints") if isinstance(context.get("constraints"), dict) else {}
    capabilities = context.get("capabilities") if isinstance(context.get("capabilities"), dict) else {}
    local_context = context.get("context") if isinstance(context.get("context"), dict) else {}
    return {
        "turn_id": str(context.get("turn_id") or ""),
        "source": str(context.get("source") or "owner_private"),
        "user_text": str(context.get("user_text") or "")[:1200],
        "context": local_context,
        "capabilities": {
            "codex_available": bool(capabilities.get("codex_available", False)),
            "external_api_available": bool(capabilities.get("external_api_available", False)),
            "local_tools_available": bool(capabilities.get("local_tools_available", True)),
        },
        "constraints": {
            "max_reply_chars": int(constraints.get("max_reply_chars") or 240),
            "allow_tool_request": False,
            "allow_memory_candidate": False,
        },
    }


def _visible_reply_from_tinykernel(response: dict[str, Any], context: dict[str, Any]) -> str:
    mode = str(response.get("mode") or "reply").strip()
    if mode not in {"reply", "clarify", "local_only_limitation"}:
        return ""
    reply = str(response.get("reply_candidate") or response.get("reply") or "").strip()
    if not reply or reply == "[WAITING]":
        return ""
    constraints = context.get("constraints") if isinstance(context.get("constraints"), dict) else {}
    try:
        max_chars = int(constraints.get("max_reply_chars") or 240)
    except (TypeError, ValueError):
        max_chars = 240
    max_chars = max(1, min(1000, max_chars))
    return reply[:max_chars]


def _record_failover_trace(
    context: dict[str, Any],
    *,
    response: dict[str, Any],
    ok: bool,
    error: str,
    elapsed_ms: float,
    primary_error: BaseException,
) -> None:
    trace_root = str(context.get("trace_root") or "").strip()
    if not trace_root:
        return
    user_text = str(context.get("user_text") or "")
    row = {
        "event_kind": "tinykernel_visible_failover",
        "observed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "turn_id": str(context.get("turn_id") or ""),
        "scope": str(context.get("scope") or ""),
        "source": str(context.get("source") or ""),
        "ok": bool(ok),
        "mode": str(response.get("mode") or ""),
        "request_hash": "sha256:" + hashlib.sha256(user_text.encode("utf-8")).hexdigest(),
        "request_chars": len(user_text),
        "reply_chars": len(str(response.get("reply_candidate") or response.get("reply") or "")),
        "confidence": float(response.get("confidence") or 0.0),
        "elapsed_ms": elapsed_ms,
        "primary_error_type": type(primary_error).__name__,
        "primary_status": _status_code(primary_error),
        "error": error,
        "notes": [str(item) for item in response.get("notes", [])] if isinstance(response.get("notes"), list) else [],
    }
    try:
        trace_path = Path(trace_root) / TRACE_REL
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception as exc:
        logger.debug("tinykernel_failover_trace_write_failed", error=str(exc))


class VisibleFailoverLLMProvider:
    """LLM provider wrapper that falls back to TinyKernel on API failures."""

    def __init__(self, primary: Any, failover: TinyKernelVisibleFailover | None = None):
        self.primary = primary
        self._failover = failover or TinyKernelVisibleFailover()
        self._fallback_active_last = False
        self.config = getattr(primary, "config", LLMConfig(model=getattr(primary, "model", "")))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.primary, name)

    @property
    def provider_name(self) -> str:
        return getattr(self.primary, "provider_name", "")

    @provider_name.setter
    def provider_name(self, value: str) -> None:
        setattr(self.primary, "provider_name", value)

    @property
    def provider_native_tools(self) -> frozenset[str]:
        return getattr(self.primary, "provider_native_tools", frozenset())

    @provider_native_tools.setter
    def provider_native_tools(self, value: Any) -> None:
        setattr(self.primary, "provider_native_tools", frozenset(value or ()))

    @property
    def prompt_cache_key(self) -> str | None:
        return getattr(self.primary, "prompt_cache_key", None)

    @prompt_cache_key.setter
    def prompt_cache_key(self, value: str | None) -> None:
        setattr(self.primary, "prompt_cache_key", value)

    @property
    def last_tool_calls(self) -> list[NativeToolCall]:
        if self._fallback_active_last:
            return []
        return getattr(self.primary, "last_tool_calls", [])

    @property
    def last_usage(self) -> dict[str, int]:
        if self._fallback_active_last:
            return {}
        return getattr(self.primary, "last_usage", {})

    @property
    def last_assistant_content_parts(self) -> list[Any] | None:
        if self._fallback_active_last:
            return None
        return getattr(self.primary, "last_assistant_content_parts", None)

    def translate_provider_native_tool(self, tool: Any) -> dict | None:
        translator = getattr(self.primary, "translate_provider_native_tool", None)
        if callable(translator):
            return translator(tool)
        return None

    async def __aenter__(self) -> "VisibleFailoverLLMProvider":
        enter = getattr(self.primary, "__aenter__", None)
        if callable(enter):
            await enter()
        return self

    async def __aexit__(self, *args: Any) -> None:
        exit_ = getattr(self.primary, "__aexit__", None)
        if callable(exit_):
            await exit_(*args)
            return
        close = getattr(self.primary, "close", None)
        if callable(close):
            await close()

    async def close(self) -> None:
        close = getattr(self.primary, "close", None)
        if callable(close):
            await close()

    async def chat(
        self,
        messages: list[Any],
        *,
        stream: bool = True,
        tools: list[ToolSchema] | None = None,
        provider_native_tools: list[Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        self._fallback_active_last = False
        context = self._active_failover_context(tools=tools, provider_native_tools=provider_native_tools)
        if context is None:
            async for chunk in self.primary.chat(
                messages,
                stream=stream,
                tools=tools,
                provider_native_tools=provider_native_tools,
                **kwargs,
            ):
                yield chunk
            return

        yielded = False
        try:
            async for chunk in self.primary.chat(
                messages,
                stream=stream,
                tools=tools,
                provider_native_tools=provider_native_tools,
                **kwargs,
            ):
                if chunk:
                    yielded = True
                yield chunk
        except Exception as exc:
            if yielded or not is_recoverable_llm_error(exc):
                raise
            reply = await self._failover.complete(context, primary_error=exc)
            self._fallback_active_last = True
            logger.warning(
                "tinykernel_visible_failover_used",
                primary_error=type(exc).__name__,
                scope=context.get("scope"),
            )
            yield reply

    async def chat_complete(self, messages: list[Any], **kwargs: Any) -> ChatResponse:
        self._fallback_active_last = False
        context = self._active_failover_context(
            tools=kwargs.get("tools"),
            provider_native_tools=kwargs.get("provider_native_tools"),
        )
        try:
            return await self.primary.chat_complete(messages, **kwargs)
        except Exception as exc:
            if context is None or not is_recoverable_llm_error(exc):
                raise
            reply = await self._failover.complete(context, primary_error=exc)
            self._fallback_active_last = True
            logger.warning(
                "tinykernel_visible_failover_used",
                primary_error=type(exc).__name__,
                scope=context.get("scope"),
            )
            return ChatResponse(
                content=reply,
                finish_reason="tinykernel_failover",
                usage={},
                model="tinykernel-visible-failover",
            )

    def _active_failover_context(
        self,
        *,
        tools: list[ToolSchema] | None,
        provider_native_tools: list[Any] | None,
    ) -> dict[str, Any] | None:
        if tools or provider_native_tools:
            return None
        context = getattr(self, "_xinyu_llm_failover_context", None)
        if not isinstance(context, dict) or not context.get("enabled"):
            return None
        if context.get("scope") != "owner_private_chat":
            return None
        return context
