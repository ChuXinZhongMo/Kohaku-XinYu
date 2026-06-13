from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_external_plugin_response_common import external_plugin_response_payload, limited_notes


def codex_execution_response(
    *,
    plugin_id: str,
    capability: str,
    prepared: dict[str, Any],
    execution: dict[str, Any],
    result: dict[str, Any],
    sessions: int,
    safe_str: Callable[..., str],
) -> dict[str, Any]:
    ok = bool(result.get("accepted"))
    return external_plugin_response_payload(
        ok=ok,
        accepted=ok,
        result="success" if ok else "failure",
        plugin_id=plugin_id,
        capability=capability,
        prepared=prepared,
        execution=execution,
        summary=[safe_str(result.get("reply"), "Codex delegate returned")],
        memory_changed=bool(result.get("memory_changed")),
        sessions=sessions,
        notes=[
            "external_plugin_codex_execute",
            *limited_notes(result.get("notes", []), 5, safe_str),
        ],
    )


def http_execution_response(
    *,
    plugin_id: str,
    capability: str,
    prepared: dict[str, Any],
    execution: dict[str, Any],
    summary: list[str],
    sessions: int,
    safe_str: Callable[..., str],
) -> dict[str, Any]:
    ok = bool(execution.get("ok"))
    return external_plugin_response_payload(
        ok=ok,
        accepted=ok,
        result="success" if ok else "failure",
        plugin_id=plugin_id,
        capability=capability,
        prepared=prepared,
        execution=execution,
        summary=summary,
        error_code="" if ok else safe_str(execution.get("error_code"), "external_http_failed"),
        sessions=sessions,
        notes=[
            "external_plugin_http_execute",
            *limited_notes(execution.get("notes", []), 4, safe_str),
        ],
    )


def private_native_execution_response(
    *,
    plugin_id: str,
    capability: str,
    prepared: dict[str, Any],
    execution: dict[str, Any],
    sessions: int,
    safe_str: Callable[..., str],
) -> dict[str, Any]:
    ok = bool(execution.get("ok"))
    return external_plugin_response_payload(
        ok=ok,
        accepted=ok,
        result="success" if ok else "blocked_by_boundary",
        plugin_id=plugin_id,
        capability=capability,
        prepared=prepared,
        execution=execution,
        summary=[f"{plugin_id}:{capability} {safe_str(execution.get('result'), 'done')}"],
        error_code="" if ok else safe_str(execution.get("error_code"), "blocked"),
        sessions=sessions,
        notes=["private_ecosystem_native_execute"],
    )
