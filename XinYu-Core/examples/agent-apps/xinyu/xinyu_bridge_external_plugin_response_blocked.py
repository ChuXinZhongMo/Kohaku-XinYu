from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_external_plugin_response_common import external_plugin_response_payload, limited_notes


def runtime_boundary_blocked_response(
    *,
    plugin_id: str,
    capability: str,
    reason: str,
    plugin_state: dict[str, Any],
    sessions: int,
) -> dict[str, Any]:
    return external_plugin_response_payload(
        ok=False,
        accepted=False,
        result="blocked_by_boundary",
        plugin_id=plugin_id,
        capability=capability,
        plugin=plugin_state,
        summary=[f"{plugin_id}:{capability} blocked: {reason}"],
        error_code=reason,
        sessions=sessions,
        notes=["external_plugin_control_blocked"],
    )


def prepared_boundary_blocked_response(
    *,
    plugin_id: str,
    capability: str,
    prepared: dict[str, Any],
    decision: dict[str, Any],
    sessions: int,
    safe_str: Callable[..., str],
) -> dict[str, Any]:
    reason = safe_str(decision.get("reason"), "blocked")
    return external_plugin_response_payload(
        ok=False,
        accepted=False,
        result="blocked_by_boundary",
        plugin_id=plugin_id,
        capability=capability,
        prepared=prepared,
        summary=[f"{plugin_id}:{capability} blocked: {reason}"],
        error_code=reason,
        sessions=sessions,
        notes=[
            "external_plugin_blocked",
            *limited_notes(decision.get("notes", []), 4, safe_str),
        ],
    )


def prepared_response(
    *,
    plugin_id: str,
    capability: str,
    prepared: dict[str, Any],
    summary: list[str],
    sessions: int,
) -> dict[str, Any]:
    return external_plugin_response_payload(
        ok=True,
        accepted=True,
        result="prepared",
        plugin_id=plugin_id,
        capability=capability,
        prepared=prepared,
        summary=summary,
        sessions=sessions,
        notes=["external_plugin_prepared"],
    )


def transport_not_configured_response(
    *,
    plugin_id: str,
    capability: str,
    prepared: dict[str, Any],
    transport: str,
    sessions: int,
) -> dict[str, Any]:
    code = f"{transport}_executor_not_configured"
    return external_plugin_response_payload(
        ok=False,
        accepted=False,
        result="failure",
        plugin_id=plugin_id,
        capability=capability,
        prepared=prepared,
        execution={"ok": False, "executed": False, "transport": transport, "error_code": code},
        summary=[f"{plugin_id}:{capability} prepared but {transport} execution is not wired yet"],
        error_code=code,
        sessions=sessions,
        notes=["external_plugin_transport_not_executed"],
    )
