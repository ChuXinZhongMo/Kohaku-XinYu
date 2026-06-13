from __future__ import annotations

from typing import Any

import xinyu_bridge_desktop_recent_routes
from xinyu_proactive_context_adapter import runtime_owner_private_turns


def install_desktop_recent_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls.desktop_events_recent = xinyu_bridge_desktop_recent_routes.desktop_events_recent
    runtime_cls.desktop_chat_recent = xinyu_bridge_desktop_recent_routes.desktop_chat_recent
    runtime_cls.desktop_memory_recent = xinyu_bridge_desktop_recent_routes.desktop_memory_recent
    runtime_cls.desktop_memory_growth_candidates = xinyu_bridge_desktop_recent_routes.desktop_memory_growth_candidates
    runtime_cls._desktop_remember_turn = xinyu_bridge_desktop_recent_routes.desktop_remember_turn
    runtime_cls._desktop_recent_owner_private_turns = runtime_owner_private_turns
    runtime_cls._desktop_remember_memory_event = xinyu_bridge_desktop_recent_routes.desktop_remember_memory_event
