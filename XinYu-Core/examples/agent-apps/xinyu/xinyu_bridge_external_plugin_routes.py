from __future__ import annotations

from typing import Any

from xinyu_bridge_external_plugin_call import external_plugin_call_impl
from xinyu_bridge_external_plugin_native import (
    execute_private_ecosystem_native_impl,
    run_private_ecosystem_native_call_impl,
)
from xinyu_bridge_external_plugin_route_bindings import (
    admin_route_deps as _build_admin_route_deps,
    ensure_open as _ensure_open,
    ensure_payload as _ensure_payload,
    external_plugin_call_deps as _build_external_plugin_call_deps,
    external_plugin_context as _build_external_plugin_context,
    external_plugin_summary as _external_plugin_summary,
    facade_deps as _build_facade_deps,
    private_native_call_deps as _build_private_native_call_deps,
    private_native_execute_deps as _build_private_native_execute_deps,
    self_thought_external_plugin_deps as _build_self_thought_external_plugin_deps,
    sessions as _sessions,
)
from xinyu_bridge_external_plugin_route_admin import (
    external_plugin_config_impl,
    external_plugin_install_impl,
    external_plugin_manifest_impl,
)
from xinyu_bridge_external_action_route_backend import maybe_execute_external_action_backend
from xinyu_bridge_external_plugin_route_self_thought import (
    maybe_run_self_thought_external_plugin_route,
)
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import as_int as _as_int
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_external_plugins import (
    ExternalCallContext,
    execute_http_prepared_call,
    external_plugin_runtime_allowed,
    external_plugin_status as build_external_plugin_status,
    install_external_plugin,
    prepare_external_call,
    save_external_plugin_control_patch,
)


def _facade_deps():
    return _build_facade_deps(
        as_bool=_as_bool,
        as_int=_as_int,
        safe_str=_safe_str,
        runtime_allowed=external_plugin_runtime_allowed,
        prepare_call=prepare_external_call,
        execute_http=execute_http_prepared_call,
        build_status=build_external_plugin_status,
        save_control_patch=save_external_plugin_control_patch,
        install_plugin=install_external_plugin,
    )


def _external_plugin_context(payload: dict[str, Any]) -> ExternalCallContext:
    return _build_external_plugin_context(payload, _facade_deps)


def maybe_run_self_thought_external_plugin(
    runtime: Any,
    *,
    thought: dict[str, Any],
    checked_at: str,
) -> list[str]:
    return maybe_run_self_thought_external_plugin_route(
        runtime,
        thought=thought,
        checked_at=checked_at,
        deps=_self_thought_external_plugin_deps(),
    )


def _self_thought_external_plugin_deps():
    return _build_self_thought_external_plugin_deps(_facade_deps)


def _execute_private_ecosystem_native(
    root: Any,
    plugin_id: str,
    capability: str,
    args: dict[str, Any],
    context: ExternalCallContext,
) -> dict[str, Any]:
    return execute_private_ecosystem_native_impl(
        root,
        plugin_id,
        capability,
        args,
        context,
        deps=_private_native_execute_deps(),
    )


def _private_native_execute_deps():
    return _build_private_native_execute_deps(_facade_deps)


def run_private_ecosystem_native_call(
    root: Any,
    plugin_id: str,
    capability: str,
    args: dict[str, Any],
    context: ExternalCallContext,
    *,
    execute: bool = True,
) -> dict[str, Any]:
    return run_private_ecosystem_native_call_impl(
        root,
        plugin_id,
        capability,
        args,
        context,
        execute=execute,
        deps=_private_native_call_deps(),
    )


def _private_native_call_deps():
    return _build_private_native_call_deps(_execute_private_ecosystem_native, _facade_deps)


async def external_plugin_manifest(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/external/plugins",
        http_method="GET",
        runtime_method="external_plugin_manifest",
    )
    if backend_response is not None:
        return backend_response
    return await external_plugin_manifest_impl(runtime, payload, _admin_route_deps())


async def external_plugin_config(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/external/plugins/config",
        http_method="POST",
        runtime_method="external_plugin_config",
    )
    if backend_response is not None:
        return backend_response
    return await external_plugin_config_impl(runtime, payload, _admin_route_deps())


async def external_plugin_install(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/external/plugins/install",
        http_method="POST",
        runtime_method="external_plugin_install",
    )
    if backend_response is not None:
        return backend_response
    return await external_plugin_install_impl(runtime, payload, _admin_route_deps())


def _admin_route_deps():
    return _build_admin_route_deps(_facade_deps)


def _external_plugin_call_deps():
    return _build_external_plugin_call_deps(_execute_private_ecosystem_native, _facade_deps)


async def external_plugin_call(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_response = await maybe_execute_external_action_backend(
        runtime,
        payload,
        route="/external/call",
        http_method="POST",
        runtime_method="external_plugin_call",
    )
    if backend_response is not None:
        return backend_response
    return await external_plugin_call_impl(runtime, payload, _external_plugin_call_deps())
