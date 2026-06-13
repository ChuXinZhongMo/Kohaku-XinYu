from __future__ import annotations

from typing import Any, Callable

import xinyu_bridge_desktop_proactive_inbox as _proactive_inbox
from xinyu_bridge_desktop_proactive_deps_support import DesktopProactiveDeps


def desktop_remember_proactive_history(
    runtime: Any,
    item: dict[str, Any],
    *,
    compact_history: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    deps: DesktopProactiveDeps,
) -> None:
    _proactive_inbox.desktop_remember_proactive_history(
        runtime,
        item,
        safe_str=deps.safe_str,
        compact_history=compact_history,
        history_rel=deps.history_rel,
        append_jsonl_func=deps.append_jsonl,
    )


def desktop_load_proactive_history(
    runtime: Any,
    *,
    compact_history: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    deps: DesktopProactiveDeps,
) -> None:
    _proactive_inbox.desktop_load_proactive_history(
        runtime,
        safe_str=deps.safe_str,
        compact_history=compact_history,
        history_rel=deps.history_rel,
        history_max=deps.history_max,
    )


def desktop_compact_proactive_history(
    rows: list[dict[str, Any]],
    *,
    deps: DesktopProactiveDeps,
) -> list[dict[str, Any]]:
    return _proactive_inbox.desktop_compact_proactive_history(
        rows,
        safe_str=deps.safe_str,
        history_max=deps.history_max,
    )
