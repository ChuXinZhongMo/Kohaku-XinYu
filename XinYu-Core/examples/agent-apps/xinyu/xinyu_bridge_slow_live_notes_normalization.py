from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_values import safe_str as _safe_str


def notes_from_sidecar(
    sidecar: dict[str, Any],
    limit: int,
    *,
    safe_str_func: Callable[..., str] = _safe_str,
) -> list[str]:
    return [safe_str_func(note) for note in sidecar.get("notes", [])[:limit]]


def extend_sidecar_notes(
    notes: list[str],
    sidecars: tuple[tuple[dict[str, Any], int], ...],
    *,
    notes_from_sidecar_func: Callable[..., list[str]],
) -> None:
    for sidecar, limit in sidecars:
        notes.extend(notes_from_sidecar_func(sidecar, limit))


def filtered_sticker_notes(
    sticker_reply: dict[str, Any],
    *,
    safe_str_func: Callable[..., str],
) -> list[str]:
    sticker_notes: list[str] = []
    for raw_note in sticker_reply.get("notes", []):
        note = safe_str_func(raw_note)
        if note and not note.startswith("sticker_skip:not_requested"):
            sticker_notes.append(note)
    return sticker_notes[:3]
