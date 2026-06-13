from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class DesktopProactiveDeps:
    safe_str: Callable[..., str]
    dedupe: Callable[..., list[Any]]
    as_bool: Callable[..., bool]
    read_text_safe: Callable[..., str]
    state_field: Callable[..., str]
    desktop_hash: Callable[..., str]
    desktop_text_preview: Callable[..., str]
    compose_visible_message: Callable[..., str]
    record_initiative_feedback: Callable[..., dict[str, Any]]
    runtime_owner_private_turns: Callable[..., list[Any]]
    enqueue_qq_outbox_message: Callable[..., dict[str, Any]]
    write_proactive_qq_dispatch_state: Callable[..., Any]
    append_jsonl: Callable[..., Any]
    atomic_write_text: Callable[..., Any]
    inbox_max: int
    history_max: int
    history_rel: Path
    inbox_statuses: set[str]
    final_statuses: set[str]
