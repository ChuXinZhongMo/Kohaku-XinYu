from __future__ import annotations

from typing import Any

import xinyu_bridge_desktop_proactive_publish as _proactive_publish
from xinyu_bridge_desktop_proactive_deps_support import DesktopProactiveDeps


async def desktop_publish_proactive_candidate_ready_from_state(
    runtime: Any,
    *,
    notes: list[str] | tuple[str, ...] | None = None,
    deps: DesktopProactiveDeps,
) -> dict[str, Any]:
    return await _proactive_publish.desktop_publish_proactive_candidate_ready_from_state(
        runtime,
        notes=notes,
        safe_str=deps.safe_str,
        dedupe=deps.dedupe,
    )


def desktop_schedule_proactive_candidate_ready_from_state(
    runtime: Any,
    *,
    notes: list[str] | tuple[str, ...] | None = None,
) -> bool:
    return _proactive_publish.desktop_schedule_proactive_candidate_ready_from_state(runtime, notes=notes)


def desktop_publish_initiative_candidate_threadsafe(
    runtime: Any,
    item: dict[str, Any],
    *,
    notes: list[str] | tuple[str, ...] | None = None,
    deps: DesktopProactiveDeps,
) -> bool:
    return _proactive_publish.desktop_publish_initiative_candidate_threadsafe(
        runtime,
        item,
        notes=notes,
        safe_str=deps.safe_str,
        dedupe=deps.dedupe,
    )


async def desktop_publish_proactive_delivery_item(
    runtime: Any,
    item: dict[str, Any],
    *,
    status_override: str = "",
    notes: list[str] | tuple[str, ...] | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    return await _proactive_publish.desktop_publish_proactive_delivery_item(
        runtime,
        item,
        status_override=status_override,
        notes=notes,
        severity=severity,
    )


async def desktop_publish_proactive_delivery_from_state(
    runtime: Any,
    *,
    status_override: str = "",
    notes: list[str] | tuple[str, ...] | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    return await _proactive_publish.desktop_publish_proactive_delivery_from_state(
        runtime,
        status_override=status_override,
        notes=notes,
        severity=severity,
    )


def desktop_publish_proactive_delivery_from_state_threadsafe(
    runtime: Any,
    *,
    status_override: str = "",
    notes: list[str] | tuple[str, ...] | None = None,
    severity: str | None = None,
) -> None:
    _proactive_publish.desktop_publish_proactive_delivery_from_state_threadsafe(
        runtime,
        status_override=status_override,
        notes=notes,
        severity=severity,
    )
