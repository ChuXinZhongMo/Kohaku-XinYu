from __future__ import annotations

from collections.abc import Callable

from xinyu_bridge_desktop_event_memory import memory_recall_notes
from xinyu_bridge_desktop_event_memory import memory_recall_remember_item
from xinyu_bridge_desktop_event_memory import memory_recall_should_skip
from xinyu_bridge_desktop_event_memory import memory_recall_top_sources
from xinyu_bridge_desktop_event_payloads import _nonempty_safe_strings
from xinyu_bridge_desktop_event_payloads import chat_finished_payload
from xinyu_bridge_desktop_event_payloads import chat_finished_severity
from xinyu_bridge_desktop_event_payloads import chat_started_payload
from xinyu_bridge_desktop_event_payloads import memory_recall_payload
from xinyu_bridge_desktop_event_publish import publish_event
from xinyu_bridge_desktop_event_publish import publish_event_threadsafe
from xinyu_bridge_desktop_event_tts import maybe_enqueue_tts


SafeStrFunc = Callable[..., str]


__all__ = [
    "SafeStrFunc",
    "chat_finished_payload",
    "chat_finished_severity",
    "chat_started_payload",
    "maybe_enqueue_tts",
    "memory_recall_notes",
    "memory_recall_payload",
    "memory_recall_remember_item",
    "memory_recall_should_skip",
    "memory_recall_top_sources",
    "publish_event",
    "publish_event_threadsafe",
]
