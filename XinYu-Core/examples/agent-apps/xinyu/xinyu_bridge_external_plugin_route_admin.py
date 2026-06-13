from __future__ import annotations

import asyncio
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Callable

from xinyu_bridge_errors import BridgeRequestError


@dataclass(frozen=True)
class ExternalPluginAdminRouteDeps:
    ensure_open: Callable[[Any], None]
    ensure_payload: Callable[[dict[str, Any] | None], dict[str, Any]]
    sessions: Callable[[Any], int]
    safe_str: Callable[..., str]
    build_status: Callable[..., dict[str, Any]]
    save_control_patch: Callable[..., dict[str, Any]]
    install_plugin: Callable[..., dict[str, Any]]


async def external_plugin_manifest_impl(
    runtime: Any,
    payload: dict[str, Any] | None,
    deps: ExternalPluginAdminRouteDeps,
) -> dict[str, Any]:
    deps.ensure_open(runtime)
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return {
        "ok": True,
        "accepted": True,
        **deps.build_status(runtime.xinyu_dir),
        "memory_changed": False,
        "session_created": False,
        "sessions": deps.sessions(runtime),
        "notes": ["external_plugin_manifest"],
    }


async def external_plugin_config_impl(
    runtime: Any,
    payload: dict[str, Any] | None,
    deps: ExternalPluginAdminRouteDeps,
) -> dict[str, Any]:
    deps.ensure_open(runtime)
    payload = deps.ensure_payload(payload)
    try:
        status = await asyncio.to_thread(deps.save_control_patch, runtime.xinyu_dir, payload)
    except ValueError as exc:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, str(exc)) from exc
    return {
        "accepted": True,
        **status,
        "memory_changed": False,
        "session_created": False,
        "sessions": deps.sessions(runtime),
        "notes": ["external_plugin_config_saved"],
    }


async def external_plugin_install_impl(
    runtime: Any,
    payload: dict[str, Any] | None,
    deps: ExternalPluginAdminRouteDeps,
) -> dict[str, Any]:
    deps.ensure_open(runtime)
    payload = deps.ensure_payload(payload)
    plugin_id = deps.safe_str(payload.get("plugin_id") or payload.get("pluginId")).strip()
    if not plugin_id:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "plugin_id is required")
    options = payload.get("options") if isinstance(payload.get("options"), dict) else {}
    try:
        result = await asyncio.to_thread(deps.install_plugin, runtime.xinyu_dir, plugin_id, options)
    except ValueError as exc:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, str(exc)) from exc
    return {
        "accepted": bool(result.get("ok")),
        "memory_changed": False,
        "session_created": False,
        "sessions": deps.sessions(runtime),
        **result,
    }


__all__ = [
    "ExternalPluginAdminRouteDeps",
    "external_plugin_config_impl",
    "external_plugin_install_impl",
    "external_plugin_manifest_impl",
]
