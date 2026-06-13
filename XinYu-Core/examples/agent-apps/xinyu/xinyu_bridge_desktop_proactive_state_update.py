from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Callable


def desktop_update_proactive_request_state(
    root: Path,
    *,
    candidate_id: str,
    status: str,
    answer_state: str = "",
    ack_status: str = "",
    adapter_message_id: str = "",
    adapter_error: str = "",
    claim_id: str = "",
    read_text_safe_func: Callable[..., str],
    safe_str_func: Callable[..., str],
    atomic_write_text_func: Callable[..., Any],
    current_item_func: Callable[..., dict[str, Any]],
    replace_frontmatter_field_func: Callable[[str, str, str], str],
    replace_list_field_func: Callable[[str, str, str], str],
    refresh_feedback_func: Callable[..., Any],
) -> dict[str, Any]:
    path = root / "memory/context/proactive_request_state.md"
    state = read_text_safe_func(path)
    if not state:
        return {}
    current = current_item_func(include_final=True)
    if safe_str_func(current.get("candidateId")) != candidate_id:
        return {}
    updated_at = datetime.now().astimezone().isoformat()
    updated = replace_frontmatter_field_func(state, "updated_at", updated_at)
    updated = replace_list_field_func(updated, "status", status)
    if answer_state:
        updated = replace_list_field_func(updated, "request_answer_state", answer_state)
    if ack_status:
        updated = replace_list_field_func(updated, "last_ack_status", ack_status)
        updated = replace_list_field_func(updated, "last_acked_at", updated_at)
    if claim_id:
        updated = replace_list_field_func(updated, "last_claim_id", claim_id)
    if adapter_message_id:
        updated = replace_list_field_func(updated, "adapter_message_id", adapter_message_id)
    if adapter_error:
        updated = replace_list_field_func(updated, "adapter_error", adapter_error)
    atomic_write_text_func(path, updated.rstrip())
    if status in {"answered", "dismissed", "read_locally"} or answer_state in {
        "owner_replied",
        "dismissed",
        "read_locally",
    }:
        refresh_feedback_func(
            trigger=f"desktop_proactive_{answer_state or status}",
            checked_at=updated_at,
        )
    return current_item_func(include_final=True)
