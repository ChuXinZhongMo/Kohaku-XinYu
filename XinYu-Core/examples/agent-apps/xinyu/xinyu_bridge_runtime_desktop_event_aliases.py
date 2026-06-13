from __future__ import annotations

from typing import Any

import xinyu_bridge_desktop_events
from xinyu_desktop_service import desktop_limit as desktop_service_limit


def install_desktop_event_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._desktop_limit = staticmethod(desktop_service_limit)
    runtime_cls._desktop_publish_event = xinyu_bridge_desktop_events.desktop_publish_event
    runtime_cls._desktop_publish_event_threadsafe = xinyu_bridge_desktop_events.desktop_publish_event_threadsafe
    runtime_cls._desktop_publish_chat_started = xinyu_bridge_desktop_events.desktop_publish_chat_started
    runtime_cls._desktop_publish_chat_finished = xinyu_bridge_desktop_events.desktop_publish_chat_finished
    runtime_cls._desktop_publish_memory_recall = xinyu_bridge_desktop_events.desktop_publish_memory_recall
    runtime_cls._maybe_enqueue_tts = xinyu_bridge_desktop_events.maybe_enqueue_tts
