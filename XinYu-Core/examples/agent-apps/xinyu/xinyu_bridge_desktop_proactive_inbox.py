from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_desktop_proactive_state_store import append_desktop_proactive_history_jsonl
from xinyu_bridge_desktop_surface_snapshot_state_backend import desktop_surface_snapshot_state_backend_for_runtime
from xinyu_bridge_desktop_surface_state_store import desktop_surface_state_store_for_runtime
from xinyu_bridge_desktop_proactive_inbox_history import (
    DESKTOP_PROACTIVE_HISTORY_MAX,
    DESKTOP_PROACTIVE_HISTORY_REL,
    compact_desktop_proactive_history,
    parse_desktop_proactive_history_jsonl,
)
from xinyu_bridge_desktop_proactive_inbox_payload import build_desktop_proactive_inbox_payload
from xinyu_bridge_desktop_proactive_inbox_state import (
    DESKTOP_PROACTIVE_FINAL_STATUSES,
    DESKTOP_PROACTIVE_INBOX_MAX,
    DESKTOP_PROACTIVE_INBOX_STATUSES,
)
from xinyu_bridge_values import safe_str as _safe_str


async def desktop_proactive_inbox(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    safe_str: Callable[..., str] = _safe_str,
    inbox_max: int = DESKTOP_PROACTIVE_INBOX_MAX,
    history_max: int = DESKTOP_PROACTIVE_HISTORY_MAX,
    load_history_func: Callable[[], Any] | None = None,
    state_item_func: Callable[..., dict[str, Any]] | None = None,
    upsert_inbox_func: Callable[[dict[str, Any]], Any] | None = None,
    remove_state_items_func: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    _ = payload
    if load_history_func is not None:
        load_history_func()
    state_item = state_item_func() if state_item_func is not None else {}
    if state_item:
        if upsert_inbox_func is not None:
            upsert_inbox_func(state_item)
    elif remove_state_items_func is not None:
        remove_state_items_func()
    state_store = desktop_surface_state_store_for_runtime(runtime)
    return build_desktop_proactive_inbox_payload(
        state_store.proactive_inbox_items(),
        state_store.proactive_history_items(),
        safe_str=safe_str,
        inbox_max=inbox_max,
        history_max=history_max,
    )


def desktop_proactive_existing(runtime: Any, candidate_id: str) -> dict[str, Any]:
    return desktop_surface_state_store_for_runtime(runtime).proactive_existing(candidate_id)


def desktop_upsert_proactive_inbox(
    runtime: Any,
    item: dict[str, Any],
    *,
    safe_str: Callable[..., str] = _safe_str,
) -> None:
    desktop_surface_state_store_for_runtime(runtime).proactive_upsert(item, safe_str=safe_str)


def desktop_remove_proactive_inbox(runtime: Any, candidate_id: str) -> None:
    desktop_surface_state_store_for_runtime(runtime).proactive_remove(candidate_id)


def desktop_remove_proactive_state_items(
    runtime: Any,
    *,
    safe_str: Callable[..., str] = _safe_str,
) -> None:
    desktop_surface_state_store_for_runtime(runtime).proactive_remove_state_items(safe_str=safe_str)


def desktop_clear_proactive_inbox(runtime: Any) -> None:
    desktop_surface_state_store_for_runtime(runtime).proactive_clear()


def desktop_prune_proactive_inbox(
    runtime: Any,
    *,
    safe_str: Callable[..., str] = _safe_str,
    final_statuses: set[str] = DESKTOP_PROACTIVE_FINAL_STATUSES,
    expired_func: Callable[[str], bool] | None = None,
) -> None:
    expired = expired_func or getattr(runtime, "_desktop_proactive_expired")
    desktop_surface_state_store_for_runtime(runtime).proactive_prune(
        safe_str=safe_str,
        expired=expired,
        final_statuses=final_statuses,
    )


def desktop_remember_proactive_history(
    runtime: Any,
    item: dict[str, Any],
    *,
    safe_str: Callable[..., str] = _safe_str,
    compact_history: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
    history_rel: Path = DESKTOP_PROACTIVE_HISTORY_REL,
    append_jsonl_func: Callable[[Path, dict[str, Any]], Any] = append_desktop_proactive_history_jsonl,
) -> None:
    root = desktop_surface_snapshot_state_backend_for_runtime(runtime).root(runtime)
    candidate_id = safe_str(item.get("candidateId"))
    if not candidate_id:
        return
    compact = compact_history or desktop_compact_proactive_history
    trace_error = getattr(runtime, "_trace_autonomous", lambda _message: None)
    desktop_surface_state_store_for_runtime(runtime).proactive_remember_history(
        item,
        root=root,
        history_rel=history_rel,
        compact_history=compact,
        append_jsonl_func=append_jsonl_func,
        trace_error_func=trace_error,
        safe_str=safe_str,
    )


def desktop_load_proactive_history(
    runtime: Any,
    *,
    safe_str: Callable[..., str] = _safe_str,
    compact_history: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
    history_rel: Path = DESKTOP_PROACTIVE_HISTORY_REL,
    history_max: int = DESKTOP_PROACTIVE_HISTORY_MAX,
) -> None:
    compact = compact_history or desktop_compact_proactive_history
    root = desktop_surface_snapshot_state_backend_for_runtime(runtime).root(runtime)
    desktop_surface_state_store_for_runtime(runtime).proactive_load_history(
        root=root,
        history_rel=history_rel,
        parse_history_func=parse_desktop_proactive_history_jsonl,
        compact_history=compact,
        safe_str=safe_str,
        history_max=history_max,
    )


def desktop_compact_proactive_history(
    rows: list[dict[str, Any]],
    *,
    safe_str: Callable[..., str] = _safe_str,
    history_max: int = DESKTOP_PROACTIVE_HISTORY_MAX,
) -> list[dict[str, Any]]:
    return compact_desktop_proactive_history(rows, safe_str=safe_str, history_max=history_max)
