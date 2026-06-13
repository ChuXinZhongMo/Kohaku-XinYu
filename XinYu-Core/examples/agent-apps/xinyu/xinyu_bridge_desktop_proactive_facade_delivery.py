from __future__ import annotations

from typing import Any, Callable

import xinyu_bridge_desktop_proactive_bindings as _proactive_bindings


DepsProvider = Callable[[], Any]


def build_desktop_proactive_delivery_facade(deps_provider: DepsProvider) -> dict[str, Callable[..., Any]]:
    def record_desktop_initiative_feedback(
        runtime: Any,
        item: dict[str, Any],
        *,
        action: str,
        record_feedback: Callable[..., dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return _proactive_bindings.record_desktop_initiative_feedback(
            runtime,
            item,
            action=action,
            deps=deps_provider(),
            record_feedback=record_feedback,
        )

    def desktop_proactive_delivery_payload(
        item: dict[str, Any],
        *,
        status_override: str = "",
        notes: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        return _proactive_bindings.desktop_proactive_delivery_payload(
            item,
            status_override=status_override,
            notes=notes,
            deps=deps_provider(),
        )

    def desktop_apply_proactive_delivery(runtime: Any, payload: dict[str, Any]) -> None:
        _proactive_bindings.desktop_apply_proactive_delivery(runtime, payload, deps=deps_provider())

    async def desktop_publish_proactive_candidate_ready_from_state(
        runtime: Any,
        *,
        notes: list[str] | tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        return await _proactive_bindings.desktop_publish_proactive_candidate_ready_from_state(
            runtime,
            notes=notes,
            deps=deps_provider(),
        )

    def desktop_schedule_proactive_candidate_ready_from_state(
        runtime: Any,
        *,
        notes: list[str] | tuple[str, ...] | None = None,
    ) -> bool:
        return _proactive_bindings.desktop_schedule_proactive_candidate_ready_from_state(runtime, notes=notes)

    def desktop_publish_initiative_candidate_threadsafe(
        runtime: Any,
        item: dict[str, Any],
        *,
        notes: list[str] | tuple[str, ...] | None = None,
    ) -> bool:
        return _proactive_bindings.desktop_publish_initiative_candidate_threadsafe(
            runtime,
            item,
            notes=notes,
            deps=deps_provider(),
        )

    async def desktop_publish_proactive_delivery_item(
        runtime: Any,
        item: dict[str, Any],
        *,
        status_override: str = "",
        notes: list[str] | tuple[str, ...] | None = None,
        severity: str | None = None,
    ) -> dict[str, Any]:
        return await _proactive_bindings.desktop_publish_proactive_delivery_item(
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
        return await _proactive_bindings.desktop_publish_proactive_delivery_from_state(
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
        _proactive_bindings.desktop_publish_proactive_delivery_from_state_threadsafe(
            runtime,
            status_override=status_override,
            notes=notes,
            severity=severity,
        )

    return {
        "record_desktop_initiative_feedback": record_desktop_initiative_feedback,
        "desktop_proactive_delivery_payload": desktop_proactive_delivery_payload,
        "desktop_apply_proactive_delivery": desktop_apply_proactive_delivery,
        "desktop_publish_proactive_candidate_ready_from_state": (
            desktop_publish_proactive_candidate_ready_from_state
        ),
        "desktop_schedule_proactive_candidate_ready_from_state": (
            desktop_schedule_proactive_candidate_ready_from_state
        ),
        "desktop_publish_initiative_candidate_threadsafe": desktop_publish_initiative_candidate_threadsafe,
        "desktop_publish_proactive_delivery_item": desktop_publish_proactive_delivery_item,
        "desktop_publish_proactive_delivery_from_state": desktop_publish_proactive_delivery_from_state,
        "desktop_publish_proactive_delivery_from_state_threadsafe": (
            desktop_publish_proactive_delivery_from_state_threadsafe
        ),
    }
