from __future__ import annotations

from typing import Any

import xinyu_bridge_desktop_proactive_state_update as _proactive_state_update
from xinyu_bridge_desktop_proactive_deps_support import DesktopProactiveDeps


def desktop_update_proactive_request_state(
    runtime: Any,
    *,
    candidate_id: str,
    status: str,
    answer_state: str = "",
    ack_status: str = "",
    adapter_message_id: str = "",
    adapter_error: str = "",
    claim_id: str = "",
    deps: DesktopProactiveDeps,
) -> dict[str, Any]:
    return _proactive_state_update.desktop_update_proactive_request_state(
        runtime.xinyu_dir,
        candidate_id=candidate_id,
        status=status,
        answer_state=answer_state,
        ack_status=ack_status,
        adapter_message_id=adapter_message_id,
        adapter_error=adapter_error,
        claim_id=claim_id,
        read_text_safe_func=deps.read_text_safe,
        safe_str_func=deps.safe_str,
        atomic_write_text_func=deps.atomic_write_text,
        current_item_func=runtime._desktop_proactive_item_from_state,
        replace_frontmatter_field_func=runtime._desktop_replace_frontmatter_field,
        replace_list_field_func=runtime._desktop_replace_list_field,
        refresh_feedback_func=runtime._refresh_initiative_spine_after_proactive_feedback,
    )
