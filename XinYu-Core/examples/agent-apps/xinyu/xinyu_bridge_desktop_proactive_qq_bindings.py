from __future__ import annotations

from typing import Any, Callable

import xinyu_bridge_desktop_proactive_qq as _proactive_qq
from xinyu_bridge_desktop_proactive_deps_support import DesktopProactiveDeps


async def desktop_approve_proactive_qq(
    runtime: Any,
    item: dict[str, Any],
    *,
    current_question_func: Callable[..., str],
    deps: DesktopProactiveDeps,
) -> dict[str, Any]:
    return await _proactive_qq.desktop_approve_proactive_qq(
        runtime,
        item,
        owner_private_turns_func=deps.runtime_owner_private_turns,
        current_question_func=current_question_func,
        compose_visible_message_func=deps.compose_visible_message,
        enqueue_qq_outbox_message_func=deps.enqueue_qq_outbox_message,
        write_dispatch_state_func=deps.write_proactive_qq_dispatch_state,
        safe_str_func=deps.safe_str,
    )
