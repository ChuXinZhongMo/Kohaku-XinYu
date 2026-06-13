from __future__ import annotations

from typing import Any

import xinyu_bridge_desktop_proactive_inbox as _proactive_inbox
from xinyu_bridge_desktop_proactive_deps_support import DesktopProactiveDeps


async def desktop_proactive_inbox(
    runtime: Any,
    payload: dict[str, Any] | None,
    *,
    deps: DesktopProactiveDeps,
) -> dict[str, Any]:
    return await _proactive_inbox.desktop_proactive_inbox(
        runtime,
        payload,
        safe_str=deps.safe_str,
        inbox_max=deps.inbox_max,
        history_max=deps.history_max,
        load_history_func=runtime._desktop_load_proactive_history,
        state_item_func=runtime._desktop_proactive_item_from_state,
        upsert_inbox_func=runtime._desktop_upsert_proactive_inbox,
        remove_state_items_func=runtime._desktop_remove_proactive_state_items,
    )


def desktop_proactive_existing(runtime: Any, candidate_id: str) -> dict[str, Any]:
    return _proactive_inbox.desktop_proactive_existing(runtime, candidate_id)


def desktop_upsert_proactive_inbox(
    runtime: Any,
    item: dict[str, Any],
    *,
    deps: DesktopProactiveDeps,
) -> None:
    _proactive_inbox.desktop_upsert_proactive_inbox(runtime, item, safe_str=deps.safe_str)


def desktop_remove_proactive_inbox(runtime: Any, candidate_id: str) -> None:
    _proactive_inbox.desktop_remove_proactive_inbox(runtime, candidate_id)


def desktop_remove_proactive_state_items(
    runtime: Any,
    *,
    deps: DesktopProactiveDeps,
) -> None:
    _proactive_inbox.desktop_remove_proactive_state_items(runtime, safe_str=deps.safe_str)


def desktop_clear_proactive_inbox(runtime: Any) -> None:
    _proactive_inbox.desktop_clear_proactive_inbox(runtime)


def desktop_prune_proactive_inbox(
    runtime: Any,
    *,
    deps: DesktopProactiveDeps,
) -> None:
    _proactive_inbox.desktop_prune_proactive_inbox(
        runtime,
        safe_str=deps.safe_str,
        final_statuses=deps.final_statuses,
        expired_func=runtime._desktop_proactive_expired,
    )
