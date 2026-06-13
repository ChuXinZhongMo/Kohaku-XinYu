from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_desktop_proactive_inbox import (
    DESKTOP_PROACTIVE_FINAL_STATUSES,
    DESKTOP_PROACTIVE_INBOX_STATUSES,
)
from xinyu_bridge_desktop_projection import desktop_hash as _desktop_hash
from xinyu_bridge_desktop_projection import desktop_text_preview as _desktop_text_preview
from xinyu_bridge_desktop_proactive_projection_labels import (
    desktop_current_proactive_question as _desktop_current_proactive_question,
)
from xinyu_bridge_desktop_proactive_projection_payload import (
    desktop_proactive_delivery_payload as _desktop_proactive_delivery_payload,
)
from xinyu_bridge_desktop_proactive_projection_payload import (
    desktop_proactive_item_from_state as _desktop_proactive_item_from_state,
)
from xinyu_bridge_desktop_proactive_projection_status import (
    desktop_apply_proactive_delivery as _desktop_apply_proactive_delivery,
)
from xinyu_bridge_state_text import read_text_safe as _read_text_safe
from xinyu_bridge_state_text import state_field as _state_field
from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_visible_persona_voice import compose_proactive_visible_message as _compose_visible_message


def desktop_proactive_delivery_payload(
    item: dict[str, Any],
    *,
    status_override: str = "",
    notes: list[str] | tuple[str, ...] | None = None,
    safe_str: Callable[..., str] = _safe_str,
    dedupe: Callable[..., list[Any]] = _dedupe,
    desktop_hash: Callable[..., str] = _desktop_hash,
    desktop_text_preview: Callable[..., str] = _desktop_text_preview,
) -> dict[str, Any]:
    return _desktop_proactive_delivery_payload(
        item,
        status_override=status_override,
        notes=notes,
        safe_str=safe_str,
        dedupe=dedupe,
        desktop_hash=desktop_hash,
        desktop_text_preview=desktop_text_preview,
    )


def desktop_apply_proactive_delivery(
    runtime: Any,
    payload: dict[str, Any],
    *,
    safe_str: Callable[..., str] = _safe_str,
    final_statuses: set[str] = DESKTOP_PROACTIVE_FINAL_STATUSES,
) -> None:
    _desktop_apply_proactive_delivery(
        payload,
        safe_str=safe_str,
        final_statuses=final_statuses,
        remember_history_func=runtime._desktop_remember_proactive_history,
        remove_inbox_func=runtime._desktop_remove_proactive_inbox,
        upsert_inbox_func=runtime._desktop_upsert_proactive_inbox,
    )


def desktop_proactive_item_from_state(
    runtime: Any,
    *,
    include_final: bool = False,
    read_text_safe: Callable[..., str] = _read_text_safe,
    state_field: Callable[..., str] = _state_field,
    desktop_hash: Callable[..., str] = _desktop_hash,
    desktop_text_preview: Callable[..., str] = _desktop_text_preview,
    compose_visible_message: Callable[..., str] = _compose_visible_message,
    inbox_statuses: set[str] = DESKTOP_PROACTIVE_INBOX_STATUSES,
) -> dict[str, Any]:
    return _desktop_proactive_item_from_state(
        runtime.xinyu_dir,
        include_final=include_final,
        read_text_safe=read_text_safe,
        state_field=state_field,
        desktop_hash=desktop_hash,
        desktop_text_preview=desktop_text_preview,
        compose_visible_message=compose_visible_message,
        recent_owner_private_turns_func=runtime._desktop_recent_owner_private_turns,
        expired_func=runtime._desktop_proactive_expired,
        inbox_statuses=inbox_statuses,
    )


def desktop_current_proactive_question(
    runtime: Any,
    item: dict[str, Any],
    *,
    read_text_safe: Callable[..., str] = _read_text_safe,
    state_field: Callable[..., str] = _state_field,
    safe_str: Callable[..., str] = _safe_str,
) -> str:
    return _desktop_current_proactive_question(
        runtime.xinyu_dir,
        item,
        read_text_safe=read_text_safe,
        state_field=state_field,
        safe_str=safe_str,
        item_from_state_func=getattr(runtime, "_desktop_proactive_item_from_state", None),
    )
