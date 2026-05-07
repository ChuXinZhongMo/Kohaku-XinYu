from __future__ import annotations

import asyncio
import re
import time
from collections import deque
from concurrent.futures import Future
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable


DESKTOP_EVENT_VERSION = 1
DEFAULT_MAX_EVENTS = 1000
DEFAULT_SUBSCRIBER_QUEUE_SIZE = 200
DEFAULT_MAX_STRING_CHARS = 2000
DEFAULT_MAX_LIST_ITEMS = 80
DEFAULT_MAX_DICT_ITEMS = 120

VALID_PRIVACY_VALUES = {"public", "owner_private", "internal_summary"}
VALID_SEVERITY_VALUES = {"debug", "info", "warn", "error"}


class CursorExpiredError(LookupError):
    """Raised when a desktop event cursor is no longer available for replay."""

    def __init__(self, cursor: str, *, reason: str) -> None:
        super().__init__(f"desktop event cursor unavailable: {cursor or '(empty)'} ({reason})")
        self.cursor = cursor
        self.reason = reason


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _compact_text(value: Any, *, limit: int = DEFAULT_MAX_STRING_CHARS) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if limit > 0 and len(text) > limit:
        return text[: limit - 15].rstrip() + "...[truncated]"
    return text


def _bounded_jsonish(
    value: Any,
    *,
    max_string_chars: int,
    max_list_items: int,
    max_dict_items: int,
    depth: int = 0,
) -> Any:
    if depth >= 8:
        return _compact_text(value, limit=max_string_chars)
    if isinstance(value, str):
        return _compact_text(value, limit=max_string_chars)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, dict):
        items = list(value.items())
        limited: dict[str, Any] = {}
        for key, item in items[:max_dict_items]:
            safe_key = _compact_text(key, limit=160)
            limited[safe_key] = _bounded_jsonish(
                item,
                max_string_chars=max_string_chars,
                max_list_items=max_list_items,
                max_dict_items=max_dict_items,
                depth=depth + 1,
            )
        if len(items) > max_dict_items:
            limited["_truncated_keys"] = len(items) - max_dict_items
        return limited
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        limited_items = [
            _bounded_jsonish(
                item,
                max_string_chars=max_string_chars,
                max_list_items=max_list_items,
                max_dict_items=max_dict_items,
                depth=depth + 1,
            )
            for item in items[:max_list_items]
        ]
        if len(items) > max_list_items:
            limited_items.append({"_truncated_items": len(items) - max_list_items})
        return limited_items
    return _compact_text(value, limit=max_string_chars)


@dataclass(frozen=True, slots=True)
class DesktopEventSubscription:
    bus: "DesktopEventBus"
    queue: asyncio.Queue[dict[str, Any]]
    closed: bool = False

    async def next(self) -> dict[str, Any]:
        return await self.queue.get()

    def __aiter__(self) -> "DesktopEventSubscription":
        return self

    async def __anext__(self) -> dict[str, Any]:
        if self.closed:
            raise StopAsyncIteration
        return await self.next()

    async def close(self) -> None:
        if self.closed:
            return
        object.__setattr__(self, "closed", True)
        await self.bus.unsubscribe(self)


class DesktopEventBus:
    """Asyncio-owned desktop event ring buffer with thread-safe publish entrypoints.

    The buffer and subscribers are mutated on ``loop`` only. Threads such as the
    existing ``ThreadingHTTPServer`` handlers should use ``publish_threadsafe``.
    """

    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop,
        max_events: int = DEFAULT_MAX_EVENTS,
        subscriber_queue_size: int = DEFAULT_SUBSCRIBER_QUEUE_SIZE,
        max_string_chars: int = DEFAULT_MAX_STRING_CHARS,
        max_list_items: int = DEFAULT_MAX_LIST_ITEMS,
        max_dict_items: int = DEFAULT_MAX_DICT_ITEMS,
    ) -> None:
        if max_events < 1:
            raise ValueError("max_events must be >= 1")
        if subscriber_queue_size < 1:
            raise ValueError("subscriber_queue_size must be >= 1")
        self.loop = loop
        self.max_events = max_events
        self.subscriber_queue_size = subscriber_queue_size
        self.max_string_chars = max_string_chars
        self.max_list_items = max_list_items
        self.max_dict_items = max_dict_items
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._sequence = 0

    async def publish(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        source: str = "core",
        privacy: str = "internal_summary",
        severity: str | None = None,
        event_id: str | None = None,
        ts: str | None = None,
    ) -> dict[str, Any]:
        self._assert_loop_owner()
        event = self._build_event(
            event_type,
            payload or {},
            source=source,
            privacy=privacy,
            severity=severity,
            event_id=event_id,
            ts=ts,
        )
        self._events.append(event)
        for queue in tuple(self._subscribers):
            self._put_for_subscriber(queue, event)
        return event

    def publish_threadsafe(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        source: str = "core",
        privacy: str = "internal_summary",
        severity: str | None = None,
        event_id: str | None = None,
        ts: str | None = None,
    ) -> Future[dict[str, Any]]:
        return asyncio.run_coroutine_threadsafe(
            self.publish(
                event_type,
                payload or {},
                source=source,
                privacy=privacy,
                severity=severity,
                event_id=event_id,
                ts=ts,
            ),
            self.loop,
        )

    async def recent(self, *, limit: int = 100) -> list[dict[str, Any]]:
        self._assert_loop_owner()
        if limit <= 0:
            return []
        return list(self._events)[-limit:]

    async def replay_since(self, cursor: str, *, limit: int | None = None) -> list[dict[str, Any]]:
        self._assert_loop_owner()
        cursor = str(cursor or "").strip()
        if not cursor:
            return []
        events = list(self._events)
        if not events:
            raise CursorExpiredError(cursor, reason="event_buffer_empty")
        for index, event in enumerate(events):
            if event.get("id") == cursor:
                missed = events[index + 1 :]
                return missed if limit is None or limit <= 0 else missed[:limit]
        raise CursorExpiredError(cursor, reason="cursor_not_in_buffer")

    def recent_threadsafe(self, *, limit: int = 100, timeout: float = 5.0) -> list[dict[str, Any]]:
        future = asyncio.run_coroutine_threadsafe(self.recent(limit=limit), self.loop)
        return future.result(timeout=timeout)

    def replay_since_threadsafe(
        self,
        cursor: str,
        *,
        limit: int | None = None,
        timeout: float = 5.0,
    ) -> list[dict[str, Any]]:
        future = asyncio.run_coroutine_threadsafe(self.replay_since(cursor, limit=limit), self.loop)
        return future.result(timeout=timeout)

    async def subscribe(self, *, max_queue_size: int | None = None) -> DesktopEventSubscription:
        self._assert_loop_owner()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=max_queue_size or self.subscriber_queue_size)
        self._subscribers.add(queue)
        return DesktopEventSubscription(self, queue)

    async def unsubscribe(self, subscription: DesktopEventSubscription) -> None:
        self._assert_loop_owner()
        self._subscribers.discard(subscription.queue)

    async def latest_event_id(self) -> str:
        self._assert_loop_owner()
        return str(self._events[-1]["id"]) if self._events else ""

    async def snapshot(self) -> dict[str, Any]:
        self._assert_loop_owner()
        return {
            "version": DESKTOP_EVENT_VERSION,
            "max_events": self.max_events,
            "buffer_size": len(self._events),
            "latest_event_id": await self.latest_event_id(),
            "subscriber_count": len(self._subscribers),
        }

    def _build_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        source: str,
        privacy: str,
        severity: str | None,
        event_id: str | None,
        ts: str | None,
    ) -> dict[str, Any]:
        clean_type = _compact_text(event_type, limit=160)
        if not clean_type:
            raise ValueError("event_type is required")
        clean_privacy = privacy if privacy in VALID_PRIVACY_VALUES else "internal_summary"
        clean_severity = severity if severity in VALID_SEVERITY_VALUES else None
        safe_payload = _bounded_jsonish(
            payload,
            max_string_chars=self.max_string_chars,
            max_list_items=self.max_list_items,
            max_dict_items=self.max_dict_items,
        )
        event = {
            "id": self._unique_event_id(event_id),
            "type": clean_type,
            "version": DESKTOP_EVENT_VERSION,
            "ts": ts or _now_iso(),
            "source": _compact_text(source or "core", limit=80) or "core",
            "privacy": clean_privacy,
            "payload": safe_payload if isinstance(safe_payload, dict) else {"value": safe_payload},
        }
        if clean_severity:
            event["severity"] = clean_severity
        return event

    def _unique_event_id(self, requested: str | None) -> str:
        clean = _compact_text(requested or "", limit=180)
        if clean and not self._event_id_exists(clean):
            return clean
        self._sequence += 1
        base = f"evt-{int(time.time() * 1000)}-{self._sequence:06d}"
        if not self._event_id_exists(base):
            return base
        while True:
            self._sequence += 1
            candidate = f"{base}-{self._sequence:06d}"
            if not self._event_id_exists(candidate):
                return candidate

    def _event_id_exists(self, event_id: str) -> bool:
        return any(event.get("id") == event_id for event in self._events)

    @staticmethod
    def _put_for_subscriber(queue: asyncio.Queue[dict[str, Any]], event: dict[str, Any]) -> None:
        try:
            queue.put_nowait(event)
            return
        except asyncio.QueueFull:
            pass
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass

    def _assert_loop_owner(self) -> None:
        running = asyncio.get_running_loop()
        if running is not self.loop:
            raise RuntimeError("DesktopEventBus async methods must run on the configured event loop")


def render_replay_unavailable_event(cursor: str, *, reason: str) -> dict[str, Any]:
    return {
        "id": f"evt-replay-unavailable-{int(time.time() * 1000)}",
        "type": "desktop.event_replay.unavailable",
        "version": DESKTOP_EVENT_VERSION,
        "ts": _now_iso(),
        "source": "core",
        "privacy": "internal_summary",
        "severity": "warn",
        "payload": {
            "cursor": cursor or "none",
            "reason": reason,
            "recommendedAction": "refresh_snapshot",
        },
    }


def event_types(events: Iterable[dict[str, Any]]) -> list[str]:
    return [str(event.get("type") or "") for event in events]
