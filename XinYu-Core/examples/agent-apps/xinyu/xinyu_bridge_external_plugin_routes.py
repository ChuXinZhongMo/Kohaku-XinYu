from __future__ import annotations

import asyncio
from http import HTTPStatus
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import as_int as _as_int
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_external_plugins import (
    TRANSPORT_HTTP,
    TRANSPORT_MCP,
    TRANSPORT_NATIVE_BRIDGE,
    TRANSPORT_WEBSOCKET,
    ExternalCallContext,
    execute_http_prepared_call,
    external_plugin_runtime_allowed,
    external_plugin_status as build_external_plugin_status,
    install_external_plugin,
    prepare_external_call,
    save_external_plugin_control_patch,
)


def _sessions(runtime: Any) -> int:
    return len(getattr(runtime, "_sessions", {}))


def _ensure_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return dict(payload or {})


def _ensure_open(runtime: Any) -> None:
    if getattr(runtime, "_closed", False):
        raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")


def _external_plugin_context(payload: dict[str, Any]) -> ExternalCallContext:
    context = payload.get("context")
    if not isinstance(context, dict):
        context = {}
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    return ExternalCallContext(
        source=_safe_str(context.get("source") or payload.get("source"), "bridge_external_call"),
        owner_private=_as_bool(
            context.get("owner_private", payload.get("owner_private", metadata.get("is_owner_user"))),
            default=False,
        ),
        reason=_safe_str(context.get("reason") or payload.get("reason")).strip(),
        proactive=_as_bool(context.get("proactive", payload.get("proactive")), default=False),
        approved=_as_bool(context.get("approved", payload.get("approved")), default=False),
    )


def _external_plugin_summary(
    *,
    plugin_id: str,
    capability: str,
    prepared: dict[str, Any],
    execution: dict[str, Any],
) -> list[str]:
    if not execution:
        decision = prepared.get("decision") if isinstance(prepared.get("decision"), dict) else {}
        return [f"{plugin_id}:{capability} prepared: {_safe_str(decision.get('reason'), 'ready')}"]
    if not execution.get("ok"):
        code = _safe_str(execution.get("error_code"), "failed")
        status = _safe_str(execution.get("status_code")).strip()
        suffix = f" status={status}" if status and status != "0" else ""
        return [f"{plugin_id}:{capability} failed: {code}{suffix}"]
    data = execution.get("json")
    if plugin_id == "kohaku_terrarium" and capability == "chat_creature" and isinstance(data, dict):
        response_text = _safe_str(data.get("response")).strip()
        if response_text:
            return [f"Kohaku response: {response_text[:240]}"]
    status = _safe_str(execution.get("status_code"), "ok")
    return [f"{plugin_id}:{capability} completed status={status}"]


async def external_plugin_manifest(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    status = build_external_plugin_status(runtime.xinyu_dir)
    return {
        "ok": True,
        "accepted": True,
        **status,
        "memory_changed": False,
        "session_created": False,
        "sessions": _sessions(runtime),
        "notes": ["external_plugin_manifest"],
    }


async def external_plugin_config(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    try:
        status = await asyncio.to_thread(save_external_plugin_control_patch, runtime.xinyu_dir, payload)
    except ValueError as exc:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, str(exc)) from exc
    return {
        "accepted": True,
        **status,
        "memory_changed": False,
        "session_created": False,
        "sessions": _sessions(runtime),
        "notes": ["external_plugin_config_saved"],
    }


async def external_plugin_install(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    plugin_id = _safe_str(payload.get("plugin_id") or payload.get("pluginId")).strip()
    if not plugin_id:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "plugin_id is required")
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    try:
        result = await asyncio.to_thread(install_external_plugin, runtime.xinyu_dir, plugin_id, options)
    except ValueError as exc:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, str(exc)) from exc
    return {
        "accepted": bool(result.get("ok")),
        "memory_changed": False,
        "session_created": False,
        "sessions": _sessions(runtime),
        **result,
    }


async def external_plugin_call(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    plugin_id = _safe_str(payload.get("plugin_id") or payload.get("pluginId")).strip()
    capability = _safe_str(payload.get("capability") or payload.get("capability_name")).strip()
    if not plugin_id or not capability:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "plugin_id and capability are required")
    args = payload.get("args")
    if not isinstance(args, dict):
        args = {}
    context = _external_plugin_context(payload)
    allowed, reason, plugin_state = external_plugin_runtime_allowed(
        runtime.xinyu_dir,
        plugin_id,
        proactive=context.proactive,
    )
    if not allowed:
        return {
            "ok": False,
            "accepted": False,
            "result": "blocked_by_boundary",
            "plugin_id": plugin_id,
            "capability": capability,
            "prepared": {},
            "execution": {},
            "plugin": plugin_state,
            "summary": [f"{plugin_id}:{capability} blocked: {reason}"],
            "error_code": reason,
            "memory_changed": False,
            "session_created": False,
            "sessions": _sessions(runtime),
            "notes": ["external_plugin_control_blocked"],
        }
    config = plugin_state.get("config") if isinstance(plugin_state.get("config"), dict) else {}
    if plugin_id == "kohaku_terrarium":
        args = dict(args)
        if not _safe_str(args.get("base_url")).strip() and _safe_str(config.get("base_url")).strip():
            args["base_url"] = _safe_str(config.get("base_url")).strip()
    prepared = prepare_external_call(plugin_id, capability, args, context).to_dict()
    decision = prepared.get("decision") if isinstance(prepared.get("decision"), dict) else {}
    if not bool(decision.get("ok")):
        reason = _safe_str(decision.get("reason"), "blocked")
        return {
            "ok": False,
            "accepted": False,
            "result": "blocked_by_boundary",
            "plugin_id": plugin_id,
            "capability": capability,
            "prepared": prepared,
            "execution": {},
            "summary": [f"{plugin_id}:{capability} blocked: {reason}"],
            "error_code": reason,
            "memory_changed": False,
            "session_created": False,
            "sessions": _sessions(runtime),
            "notes": ["external_plugin_blocked", *[_safe_str(note) for note in decision.get("notes", [])[:4]]],
        }

    execute = _as_bool(payload.get("execute"), default=True)
    request = prepared.get("request") if isinstance(prepared.get("request"), dict) else {}
    if not execute:
        return {
            "ok": True,
            "accepted": True,
            "result": "prepared",
            "plugin_id": plugin_id,
            "capability": capability,
            "prepared": prepared,
            "execution": {},
            "summary": _external_plugin_summary(
                plugin_id=plugin_id,
                capability=capability,
                prepared=prepared,
                execution={},
            ),
            "memory_changed": False,
            "session_created": False,
            "sessions": _sessions(runtime),
            "notes": ["external_plugin_prepared"],
        }

    transport = _safe_str(request.get("transport"))
    if transport == TRANSPORT_NATIVE_BRIDGE and _safe_str(request.get("bridge_method")) == "codex_execute":
        codex_payload = request.get("payload") if isinstance(request.get("payload"), dict) else {}
        codex_payload = dict(codex_payload)
        metadata = codex_payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata.setdefault("is_owner_user", context.owner_private)
        metadata["external_plugin_call"] = True
        metadata["external_plugin_id"] = plugin_id
        metadata["external_plugin_capability"] = capability
        codex_payload["metadata"] = metadata
        result = await runtime.codex_execute(codex_payload)
        ok = bool(result.get("accepted"))
        execution = {
            "ok": ok,
            "executed": True,
            "transport": TRANSPORT_NATIVE_BRIDGE,
            "bridge_method": "codex_execute",
            "result": result,
        }
        return {
            "ok": ok,
            "accepted": ok,
            "result": "success" if ok else "failure",
            "plugin_id": plugin_id,
            "capability": capability,
            "prepared": prepared,
            "execution": execution,
            "summary": [_safe_str(result.get("reply"), "Codex delegate returned")],
            "memory_changed": bool(result.get("memory_changed")),
            "session_created": False,
            "sessions": _sessions(runtime),
            "notes": ["external_plugin_codex_execute", *[_safe_str(note) for note in result.get("notes", [])[:5]]],
        }

    if transport == TRANSPORT_HTTP:
        timeout_seconds = _as_int(payload.get("timeout_seconds"), 30)
        execution = await asyncio.to_thread(
            execute_http_prepared_call,
            prepared,
            timeout_seconds=timeout_seconds,
        )
        ok = bool(execution.get("ok"))
        return {
            "ok": ok,
            "accepted": ok,
            "result": "success" if ok else "failure",
            "plugin_id": plugin_id,
            "capability": capability,
            "prepared": prepared,
            "execution": execution,
            "summary": _external_plugin_summary(
                plugin_id=plugin_id,
                capability=capability,
                prepared=prepared,
                execution=execution,
            ),
            "error_code": "" if ok else _safe_str(execution.get("error_code"), "external_http_failed"),
            "memory_changed": False,
            "session_created": False,
            "sessions": _sessions(runtime),
            "notes": ["external_plugin_http_execute", *[_safe_str(note) for note in execution.get("notes", [])[:4]]],
        }

    if transport in {TRANSPORT_WEBSOCKET, TRANSPORT_MCP}:
        code = f"{transport}_executor_not_configured"
        return {
            "ok": False,
            "accepted": False,
            "result": "failure",
            "plugin_id": plugin_id,
            "capability": capability,
            "prepared": prepared,
            "execution": {"ok": False, "executed": False, "transport": transport, "error_code": code},
            "summary": [f"{plugin_id}:{capability} prepared but {transport} execution is not wired yet"],
            "error_code": code,
            "memory_changed": False,
            "session_created": False,
            "sessions": _sessions(runtime),
            "notes": ["external_plugin_transport_not_executed"],
        }

    raise BridgeRequestError(HTTPStatus.BAD_REQUEST, f"unsupported external plugin transport: {transport}")
