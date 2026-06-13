from __future__ import annotations

from typing import Any

import xinyu_bridge_desktop_proactive_projection as _proactive_projection
from xinyu_bridge_desktop_proactive_deps_support import DesktopProactiveDeps


def desktop_proactive_delivery_payload(
    item: dict[str, Any],
    *,
    status_override: str = "",
    notes: list[str] | tuple[str, ...] | None = None,
    deps: DesktopProactiveDeps,
) -> dict[str, Any]:
    return _proactive_projection.desktop_proactive_delivery_payload(
        item,
        status_override=status_override,
        notes=notes,
        safe_str=deps.safe_str,
        dedupe=deps.dedupe,
        desktop_hash=deps.desktop_hash,
        desktop_text_preview=deps.desktop_text_preview,
    )


def desktop_apply_proactive_delivery(
    runtime: Any,
    payload: dict[str, Any],
    *,
    deps: DesktopProactiveDeps,
) -> None:
    _proactive_projection.desktop_apply_proactive_delivery(
        runtime,
        payload,
        safe_str=deps.safe_str,
        final_statuses=deps.final_statuses,
    )


def desktop_proactive_item_from_state(
    runtime: Any,
    *,
    include_final: bool = False,
    deps: DesktopProactiveDeps,
) -> dict[str, Any]:
    return _proactive_projection.desktop_proactive_item_from_state(
        runtime,
        include_final=include_final,
        read_text_safe=deps.read_text_safe,
        state_field=deps.state_field,
        desktop_hash=deps.desktop_hash,
        desktop_text_preview=deps.desktop_text_preview,
        compose_visible_message=deps.compose_visible_message,
        inbox_statuses=deps.inbox_statuses,
    )


def desktop_current_proactive_question(
    runtime: Any,
    item: dict[str, Any],
    *,
    deps: DesktopProactiveDeps,
) -> str:
    return _proactive_projection.desktop_current_proactive_question(
        runtime,
        item,
        read_text_safe=deps.read_text_safe,
        state_field=deps.state_field,
        safe_str=deps.safe_str,
    )
