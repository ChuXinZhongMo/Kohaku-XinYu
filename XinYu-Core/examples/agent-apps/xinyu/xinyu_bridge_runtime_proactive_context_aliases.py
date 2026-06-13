from __future__ import annotations

from typing import Any

import xinyu_bridge_proactive_context


def install_proactive_context_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._refresh_initiative_spine_after_proactive_feedback = (
        xinyu_bridge_proactive_context.refresh_initiative_spine_after_proactive_feedback
    )
    runtime_cls._owner_private_payload = xinyu_bridge_proactive_context.owner_private_payload
    runtime_cls._append_assistant_to_dialogue_tail = xinyu_bridge_proactive_context.append_assistant_to_dialogue_tail
    runtime_cls._sync_recent_proactive_to_dialogue_tail = (
        xinyu_bridge_proactive_context.sync_recent_proactive_to_dialogue_tail
    )
    runtime_cls._proactive_thread_context = xinyu_bridge_proactive_context.proactive_thread_context
    runtime_cls._mark_proactive_owner_reply = xinyu_bridge_proactive_context.mark_proactive_owner_reply
