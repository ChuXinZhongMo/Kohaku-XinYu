from __future__ import annotations

from typing import Any, cast

from xinyu_bridge_autonomous_note_dispatch_map import append_note


def append_note_without_result(
    name: str,
    deps: Any,
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    **kwargs: Any,
) -> None:
    append_note(name, deps, runtime, notes, checked_at=checked_at, **kwargs)


def append_optional_dict_note_result(
    name: str,
    deps: Any,
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    **kwargs: Any,
) -> dict[str, Any] | None:
    return cast(dict[str, Any] | None, append_note(name, deps, runtime, notes, checked_at=checked_at, **kwargs))


def append_dict_note_result(
    name: str,
    deps: Any,
    runtime: Any,
    notes: list[str],
    *,
    checked_at: str,
    **kwargs: Any,
) -> dict[str, Any]:
    return cast(dict[str, Any], append_note(name, deps, runtime, notes, checked_at=checked_at, **kwargs))
