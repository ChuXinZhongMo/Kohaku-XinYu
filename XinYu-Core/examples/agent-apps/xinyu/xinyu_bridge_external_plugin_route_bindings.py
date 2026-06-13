from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_external_plugin_route_deps import (
    ExternalPluginFacadeDeps,
    build_admin_route_deps,
    build_external_plugin_call_deps,
    build_external_plugin_context,
    build_private_native_call_deps,
    build_private_native_execute_deps,
    build_self_thought_external_plugin_deps,
    external_plugin_summary as build_external_plugin_summary,
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

FacadeFactory = Callable[[], ExternalPluginFacadeDeps]


def facade_deps(
    *,
    as_bool: Callable[..., bool] = _as_bool,
    as_int: Callable[..., int] = _as_int,
    safe_str: Callable[..., str] = _safe_str,
    runtime_allowed: Callable[..., tuple[bool, str, dict[str, Any]]] = external_plugin_runtime_allowed,
    prepare_call: Callable[..., Any] = prepare_external_call,
    execute_http: Callable[..., dict[str, Any]] = execute_http_prepared_call,
    build_status: Callable[..., dict[str, Any]] = build_external_plugin_status,
    save_control_patch: Callable[..., dict[str, Any]] = save_external_plugin_control_patch,
    install_plugin: Callable[..., dict[str, Any]] = install_external_plugin,
) -> ExternalPluginFacadeDeps:
    return ExternalPluginFacadeDeps(
        as_bool=as_bool,
        as_int=as_int,
        safe_str=safe_str,
        runtime_allowed=runtime_allowed,
        prepare_call=prepare_call,
        execute_http=execute_http,
        build_status=build_status,
        save_control_patch=save_control_patch,
        install_plugin=install_plugin,
    )


def sessions(runtime: Any) -> int:
    return len(getattr(runtime, "_sessions", {}))


def ensure_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return dict(payload or {})


def ensure_open(runtime: Any) -> None:
    if getattr(runtime, "_closed", False):
        raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")


def external_plugin_context(
    payload: dict[str, Any],
    facade_factory: FacadeFactory = facade_deps,
) -> ExternalCallContext:
    return build_external_plugin_context(payload, facade_factory())


def external_plugin_summary(
    *,
    plugin_id: str,
    capability: str,
    prepared: dict[str, Any],
    execution: dict[str, Any],
) -> list[str]:
    return build_external_plugin_summary(
        plugin_id=plugin_id,
        capability=capability,
        prepared=prepared,
        execution=execution,
        safe_str=_safe_str,
    )


def self_thought_external_plugin_deps(facade_factory: FacadeFactory = facade_deps):
    return build_self_thought_external_plugin_deps(facade_factory())


def private_native_execute_deps(facade_factory: FacadeFactory = facade_deps):
    return build_private_native_execute_deps(facade_factory())


def private_native_call_deps(
    execute_native: Callable[[Any, str, str, dict[str, Any], ExternalCallContext], dict[str, Any]],
    facade_factory: FacadeFactory = facade_deps,
):
    return build_private_native_call_deps(
        execute_native=execute_native,
        facade=facade_factory(),
    )


def admin_route_deps(facade_factory: FacadeFactory = facade_deps):
    return build_admin_route_deps(
        ensure_open=ensure_open,
        ensure_payload=ensure_payload,
        sessions=sessions,
        facade=facade_factory(),
    )


def external_plugin_call_deps(
    execute_private_native: Callable[..., dict[str, Any]],
    facade_factory: FacadeFactory = facade_deps,
):
    def build_context(payload: dict[str, Any]) -> ExternalCallContext:
        return external_plugin_context(payload, facade_factory)

    return build_external_plugin_call_deps(
        ensure_open=ensure_open,
        ensure_payload=ensure_payload,
        sessions=sessions,
        build_context=build_context,
        summarize=external_plugin_summary,
        execute_private_native=execute_private_native,
        facade=facade_factory(),
    )


__all__ = [
    "admin_route_deps",
    "ensure_open",
    "ensure_payload",
    "external_plugin_call_deps",
    "external_plugin_context",
    "external_plugin_summary",
    "facade_deps",
    "private_native_call_deps",
    "private_native_execute_deps",
    "self_thought_external_plugin_deps",
    "sessions",
]
