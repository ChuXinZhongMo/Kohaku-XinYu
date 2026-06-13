from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from xinyu_bridge_desktop_surface_contract import (
    DESKTOP_SURFACE_FALLBACK_ADAPTER,
    DESKTOP_SURFACE_ROLLBACK,
    DESKTOP_SURFACE_STATE_OWNER,
)


DESKTOP_SURFACE_STATE_STORE_RUNTIME_ATTR = "_desktop_surface_state_store"
DESKTOP_SURFACE_STATE_STORE_LEGACY_MODE = "desktop_surface_state_store_legacy_runtime_adapter"
DESKTOP_SURFACE_STATE_STORE_LOCAL_MODE = "desktop_surface_state_store_local_in_memory"
DESKTOP_SURFACE_STATE_STORE_ROLLBACK = "remove_runtime_state_store_attr_to_use_legacy_runtime_buffers"


class DesktopSurfaceStateStore(Protocol):
    mode: str

    def recent_turns(self) -> list[dict[str, Any]]:
        ...

    def recent_memory_events(self) -> list[dict[str, Any]]:
        ...

    def remember_turn(self, item: dict[str, Any], *, max_items: int) -> None:
        ...

    def remember_memory_event(self, item: dict[str, Any], *, max_items: int) -> None:
        ...

    def proactive_inbox_items(self) -> dict[str, dict[str, Any]]:
        ...

    def proactive_history_items(self) -> list[dict[str, Any]]:
        ...

    def proactive_existing(self, candidate_id: str) -> dict[str, Any]:
        ...

    def proactive_upsert(self, item: dict[str, Any], *, safe_str: Callable[..., str]) -> None:
        ...

    def proactive_remove(self, candidate_id: str) -> None:
        ...

    def proactive_remove_state_items(self, *, safe_str: Callable[..., str]) -> None:
        ...

    def proactive_clear(self) -> None:
        ...

    def proactive_prune(
        self,
        *,
        safe_str: Callable[..., str],
        expired: Callable[[str], bool],
        final_statuses: set[str],
    ) -> None:
        ...

    def proactive_remember_history(
        self,
        item: dict[str, Any],
        *,
        root: Path,
        history_rel: Path,
        compact_history: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
        append_jsonl_func: Callable[[Path, dict[str, Any]], Any],
        trace_error_func: Callable[[str], Any],
        safe_str: Callable[..., str],
    ) -> None:
        ...

    def proactive_load_history(
        self,
        *,
        root: Path,
        history_rel: Path,
        parse_history_func: Callable[..., list[dict[str, Any]]],
        compact_history: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
        safe_str: Callable[..., str],
        history_max: int,
    ) -> None:
        ...


@dataclass(frozen=True, slots=True)
class DesktopSurfaceStateStoreReadiness:
    service_id: str
    mode: str
    ready: bool
    state_owner: str
    fallback_adapter: str
    rollback: str
    notes: tuple[str, ...] = ()


class LocalDesktopSurfaceStateStore:
    mode = DESKTOP_SURFACE_STATE_STORE_LOCAL_MODE

    def __init__(
        self,
        *,
        recent_turns: list[dict[str, Any]] | None = None,
        recent_memory_events: list[dict[str, Any]] | None = None,
        proactive_inbox: dict[str, dict[str, Any]] | None = None,
        proactive_history: list[dict[str, Any]] | None = None,
    ) -> None:
        self._recent_turns = [dict(item) for item in (recent_turns or []) if isinstance(item, dict)]
        self._recent_memory_events = [
            dict(item) for item in (recent_memory_events or []) if isinstance(item, dict)
        ]
        self._proactive_inbox = _dict_mapping(proactive_inbox or {})
        self._proactive_history = _dict_items(proactive_history or [])

    def recent_turns(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._recent_turns]

    def recent_memory_events(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._recent_memory_events]

    def remember_turn(self, item: dict[str, Any], *, max_items: int) -> None:
        _append_trimmed(self._recent_turns, item, max_items=max_items)

    def remember_memory_event(self, item: dict[str, Any], *, max_items: int) -> None:
        _append_trimmed(self._recent_memory_events, item, max_items=max_items)

    def proactive_inbox_items(self) -> dict[str, dict[str, Any]]:
        return _dict_mapping(self._proactive_inbox)

    def proactive_history_items(self) -> list[dict[str, Any]]:
        return _dict_items(self._proactive_history)

    def proactive_existing(self, candidate_id: str) -> dict[str, Any]:
        return dict(self._proactive_inbox.get(candidate_id, {}))

    def proactive_upsert(self, item: dict[str, Any], *, safe_str: Callable[..., str]) -> None:
        candidate_id = safe_str(item.get("candidateId"))
        if not candidate_id:
            return
        existing = self._proactive_inbox.get(candidate_id, {})
        self._proactive_inbox[candidate_id] = {**existing, **dict(item)}

    def proactive_remove(self, candidate_id: str) -> None:
        self._proactive_inbox.pop(candidate_id, None)

    def proactive_remove_state_items(self, *, safe_str: Callable[..., str]) -> None:
        stale_ids = [
            candidate_id
            for candidate_id, item in self._proactive_inbox.items()
            if safe_str(item.get("source")) != "initiative_orchestrator"
        ]
        for candidate_id in stale_ids:
            self._proactive_inbox.pop(candidate_id, None)

    def proactive_clear(self) -> None:
        self._proactive_inbox.clear()

    def proactive_prune(
        self,
        *,
        safe_str: Callable[..., str],
        expired: Callable[[str], bool],
        final_statuses: set[str],
    ) -> None:
        stale_ids = [
            candidate_id
            for candidate_id, item in self._proactive_inbox.items()
            if safe_str(item.get("status")) in final_statuses or expired(safe_str(item.get("expiresAt")))
        ]
        for candidate_id in stale_ids:
            self._proactive_inbox.pop(candidate_id, None)

    def proactive_remember_history(
        self,
        item: dict[str, Any],
        *,
        root: Path,
        history_rel: Path,
        compact_history: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
        append_jsonl_func: Callable[[Path, dict[str, Any]], Any],
        trace_error_func: Callable[[str], Any],
        safe_str: Callable[..., str],
    ) -> None:
        history_item = _history_item(item)
        if not safe_str(history_item.get("candidateId")):
            return
        self._proactive_history = compact_history([*self._proactive_history, history_item])
        try:
            append_jsonl_func(root / history_rel, history_item)
        except OSError as exc:
            trace_error_func(f"desktop_proactive_history_append_error={exc!r}")

    def proactive_load_history(
        self,
        *,
        root: Path,
        history_rel: Path,
        parse_history_func: Callable[..., list[dict[str, Any]]],
        compact_history: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
        safe_str: Callable[..., str],
        history_max: int,
    ) -> None:
        try:
            text = (root / history_rel).read_text(encoding="utf-8-sig")
        except OSError:
            return
        rows = parse_history_func(text, safe_str=safe_str, history_max=history_max)
        if rows:
            self._proactive_history = compact_history([*rows, *self._proactive_history])


class LegacyRuntimeDesktopSurfaceStateStore:
    mode = DESKTOP_SURFACE_STATE_STORE_LEGACY_MODE

    def __init__(self, runtime: Any) -> None:
        self._runtime = runtime

    def recent_turns(self) -> list[dict[str, Any]]:
        return _dict_items(getattr(self._runtime, "_desktop_recent_turns", []) or [])

    def recent_memory_events(self) -> list[dict[str, Any]]:
        return _dict_items(getattr(self._runtime, "_desktop_recent_memory_events", []) or [])

    def remember_turn(self, item: dict[str, Any], *, max_items: int) -> None:
        buffer = _runtime_buffer(self._runtime, "_desktop_recent_turns")
        _append_trimmed(buffer, item, max_items=max_items)

    def remember_memory_event(self, item: dict[str, Any], *, max_items: int) -> None:
        buffer = _runtime_buffer(self._runtime, "_desktop_recent_memory_events")
        _append_trimmed(buffer, item, max_items=max_items)

    def proactive_inbox_items(self) -> dict[str, dict[str, Any]]:
        with _runtime_lock(self._runtime):
            return _dict_mapping(getattr(self._runtime, "_desktop_proactive_inbox", {}) or {})

    def proactive_history_items(self) -> list[dict[str, Any]]:
        with _runtime_lock(self._runtime):
            return _dict_items(getattr(self._runtime, "_desktop_proactive_history", []) or [])

    def proactive_existing(self, candidate_id: str) -> dict[str, Any]:
        with _runtime_lock(self._runtime):
            inbox = getattr(self._runtime, "_desktop_proactive_inbox", {}) or {}
            return dict(inbox.get(candidate_id, {})) if isinstance(inbox, dict) else {}

    def proactive_upsert(self, item: dict[str, Any], *, safe_str: Callable[..., str]) -> None:
        candidate_id = safe_str(item.get("candidateId"))
        if not candidate_id:
            return
        with _runtime_lock(self._runtime):
            inbox = _runtime_mapping(self._runtime, "_desktop_proactive_inbox")
            existing = inbox.get(candidate_id, {})
            inbox[candidate_id] = {**existing, **dict(item)}

    def proactive_remove(self, candidate_id: str) -> None:
        with _runtime_lock(self._runtime):
            _runtime_mapping(self._runtime, "_desktop_proactive_inbox").pop(candidate_id, None)

    def proactive_remove_state_items(self, *, safe_str: Callable[..., str]) -> None:
        with _runtime_lock(self._runtime):
            inbox = _runtime_mapping(self._runtime, "_desktop_proactive_inbox")
            stale_ids = [
                candidate_id
                for candidate_id, item in inbox.items()
                if safe_str(item.get("source")) != "initiative_orchestrator"
            ]
            for candidate_id in stale_ids:
                inbox.pop(candidate_id, None)

    def proactive_clear(self) -> None:
        with _runtime_lock(self._runtime):
            _runtime_mapping(self._runtime, "_desktop_proactive_inbox").clear()

    def proactive_prune(
        self,
        *,
        safe_str: Callable[..., str],
        expired: Callable[[str], bool],
        final_statuses: set[str],
    ) -> None:
        with _runtime_lock(self._runtime):
            inbox = _runtime_mapping(self._runtime, "_desktop_proactive_inbox")
            stale_ids = [
                candidate_id
                for candidate_id, item in inbox.items()
                if safe_str(item.get("status")) in final_statuses or expired(safe_str(item.get("expiresAt")))
            ]
            for candidate_id in stale_ids:
                inbox.pop(candidate_id, None)

    def proactive_remember_history(
        self,
        item: dict[str, Any],
        *,
        root: Path,
        history_rel: Path,
        compact_history: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
        append_jsonl_func: Callable[[Path, dict[str, Any]], Any],
        trace_error_func: Callable[[str], Any],
        safe_str: Callable[..., str],
    ) -> None:
        history_item = _history_item(item)
        if not safe_str(history_item.get("candidateId")):
            return
        with _runtime_lock(self._runtime):
            history = _runtime_list(self._runtime, "_desktop_proactive_history")
            setattr(self._runtime, "_desktop_proactive_history", compact_history([*history, history_item]))
        try:
            append_jsonl_func(root / history_rel, history_item)
        except OSError as exc:
            trace_error_func(f"desktop_proactive_history_append_error={exc!r}")

    def proactive_load_history(
        self,
        *,
        root: Path,
        history_rel: Path,
        parse_history_func: Callable[..., list[dict[str, Any]]],
        compact_history: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
        safe_str: Callable[..., str],
        history_max: int,
    ) -> None:
        try:
            text = (root / history_rel).read_text(encoding="utf-8-sig")
        except OSError:
            return
        rows = parse_history_func(text, safe_str=safe_str, history_max=history_max)
        if not rows:
            return
        with _runtime_lock(self._runtime):
            history = _runtime_list(self._runtime, "_desktop_proactive_history")
            setattr(self._runtime, "_desktop_proactive_history", compact_history([*rows, *history]))


def desktop_surface_state_store_for_runtime(
    runtime: Any,
    *,
    explicit_store: DesktopSurfaceStateStore | None = None,
) -> DesktopSurfaceStateStore:
    if explicit_store is not None:
        return explicit_store
    runtime_store = getattr(runtime, DESKTOP_SURFACE_STATE_STORE_RUNTIME_ATTR, None)
    if runtime_store is not None:
        return runtime_store
    return LegacyRuntimeDesktopSurfaceStateStore(runtime)


def desktop_surface_state_store_readiness(
    runtime: Any,
    *,
    explicit_store: DesktopSurfaceStateStore | None = None,
) -> DesktopSurfaceStateStoreReadiness:
    store = desktop_surface_state_store_for_runtime(runtime, explicit_store=explicit_store)
    return DesktopSurfaceStateStoreReadiness(
        service_id="desktop_surface",
        mode=getattr(store, "mode", type(store).__name__),
        ready=True,
        state_owner=DESKTOP_SURFACE_STATE_OWNER,
        fallback_adapter=DESKTOP_SURFACE_FALLBACK_ADAPTER,
        rollback=DESKTOP_SURFACE_STATE_STORE_ROLLBACK,
        notes=(
            "recent_and_proactive_buffers_use_state_store",
            "legacy_runtime_lists_remain_fallback_adapter",
            f"surface_rollback={DESKTOP_SURFACE_ROLLBACK}",
        ),
    )


def _runtime_buffer(runtime: Any, attr: str) -> list[dict[str, Any]]:
    value = getattr(runtime, attr, None)
    if not isinstance(value, list):
        value = []
        setattr(runtime, attr, value)
    return value


def _runtime_list(runtime: Any, attr: str) -> list[dict[str, Any]]:
    value = getattr(runtime, attr, None)
    if not isinstance(value, list):
        value = []
        setattr(runtime, attr, value)
    return value


def _runtime_mapping(runtime: Any, attr: str) -> dict[str, dict[str, Any]]:
    value = getattr(runtime, attr, None)
    if not isinstance(value, dict):
        value = {}
        setattr(runtime, attr, value)
    return value


def _runtime_lock(runtime: Any) -> Any:
    lock = getattr(runtime, "_desktop_proactive_lock", None)
    if hasattr(lock, "__enter__") and hasattr(lock, "__exit__"):
        return lock
    return nullcontext()


def _append_trimmed(buffer: list[dict[str, Any]], item: dict[str, Any], *, max_items: int) -> None:
    buffer.append(dict(item))
    overflow = len(buffer) - max(1, int(max_items))
    if overflow > 0:
        del buffer[:overflow]


def _dict_items(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    return [dict(item) for item in items if isinstance(item, dict)]


def _dict_mapping(items: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(items, dict):
        return {}
    return {str(key): dict(value) for key, value in items.items() if isinstance(value, dict)}


def _history_item(item: dict[str, Any]) -> dict[str, Any]:
    from xinyu_bridge_desktop_proactive_inbox_history import build_desktop_proactive_history_item

    return build_desktop_proactive_history_item(item)
