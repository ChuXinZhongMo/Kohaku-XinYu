from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from xinyu_bridge_external_plugin_call import ExternalPluginCallDeps
from xinyu_bridge_external_plugin_native import PrivateNativeCallDeps, PrivateNativeExecuteDeps
from xinyu_bridge_external_plugin_route_admin import ExternalPluginAdminRouteDeps
from xinyu_bridge_external_plugin_self_thought import SelfThoughtExternalPluginDeps
from xinyu_bridge_stores import append_external_plugin_trace
from xinyu_bridge_state_text import read_text_safe, state_field
from xinyu_bridge_time_utils import timestamp_or_now_iso
from xinyu_external_plugins import ExternalCallContext


@dataclass(frozen=True)
class ExternalPluginFacadeDeps:
    as_bool: Callable[..., bool]
    as_int: Callable[..., int]
    safe_str: Callable[..., str]
    runtime_allowed: Callable[..., tuple[bool, str, dict[str, Any]]]
    prepare_call: Callable[..., Any]
    execute_http: Callable[..., dict[str, Any]]
    build_status: Callable[..., dict[str, Any]]
    save_control_patch: Callable[..., dict[str, Any]]
    install_plugin: Callable[..., dict[str, Any]]


def build_external_plugin_context(payload: dict[str, Any], deps: ExternalPluginFacadeDeps) -> ExternalCallContext:
    context = payload.get("context")
    if not isinstance(context, dict):
        context = {}
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    return ExternalCallContext(
        source=deps.safe_str(context.get("source") or payload.get("source"), "bridge_external_call"),
        owner_private=deps.as_bool(
            context.get("owner_private", payload.get("owner_private", metadata.get("is_owner_user"))),
            default=False,
        ),
        reason=deps.safe_str(context.get("reason") or payload.get("reason")).strip(),
        proactive=deps.as_bool(context.get("proactive", payload.get("proactive")), default=False),
        approved=deps.as_bool(context.get("approved", payload.get("approved")), default=False),
    )


def external_plugin_summary(
    *,
    plugin_id: str,
    capability: str,
    prepared: dict[str, Any],
    execution: dict[str, Any],
    safe_str: Callable[..., str],
) -> list[str]:
    if not execution:
        decision = prepared.get("decision") if isinstance(prepared.get("decision"), dict) else {}
        return [f"{plugin_id}:{capability} prepared: {safe_str(decision.get('reason'), 'ready')}"]
    if not execution.get("ok"):
        code = safe_str(execution.get("error_code"), "failed")
        status = safe_str(execution.get("status_code")).strip()
        suffix = f" status={status}" if status and status != "0" else ""
        return [f"{plugin_id}:{capability} failed: {code}{suffix}"]
    data = execution.get("json")
    if plugin_id == "kohaku_terrarium" and capability == "chat_creature" and isinstance(data, dict):
        response_text = safe_str(data.get("response")).strip()
        if response_text:
            return [f"Kohaku response: {response_text[:240]}"]
    status = safe_str(execution.get("status_code"), "ok")
    return [f"{plugin_id}:{capability} completed status={status}"]


def build_admin_route_deps(
    *,
    ensure_open: Callable[[Any], None],
    ensure_payload: Callable[[dict[str, Any] | None], dict[str, Any]],
    sessions: Callable[[Any], int],
    facade: ExternalPluginFacadeDeps,
) -> ExternalPluginAdminRouteDeps:
    return ExternalPluginAdminRouteDeps(
        ensure_open=ensure_open,
        ensure_payload=ensure_payload,
        sessions=sessions,
        safe_str=facade.safe_str,
        build_status=facade.build_status,
        save_control_patch=facade.save_control_patch,
        install_plugin=facade.install_plugin,
    )


def build_external_plugin_call_deps(
    *,
    ensure_open: Callable[[Any], None],
    ensure_payload: Callable[[dict[str, Any] | None], dict[str, Any]],
    sessions: Callable[[Any], int],
    build_context: Callable[[dict[str, Any]], Any],
    summarize: Callable[..., list[str]],
    execute_private_native: Callable[..., dict[str, Any]],
    facade: ExternalPluginFacadeDeps,
) -> ExternalPluginCallDeps:
    return ExternalPluginCallDeps(
        ensure_open=ensure_open,
        ensure_payload=ensure_payload,
        sessions=sessions,
        build_context=build_context,
        summarize=summarize,
        as_bool=facade.as_bool,
        as_int=facade.as_int,
        safe_str=facade.safe_str,
        runtime_allowed=facade.runtime_allowed,
        prepare_call=facade.prepare_call,
        execute_http=facade.execute_http,
        execute_private_native=execute_private_native,
    )


def build_private_native_execute_deps(facade: ExternalPluginFacadeDeps) -> PrivateNativeExecuteDeps:
    return PrivateNativeExecuteDeps(safe_str=facade.safe_str, as_int=facade.as_int)


def build_private_native_call_deps(
    *,
    execute_native: Callable[[Any, str, str, dict[str, Any], ExternalCallContext], dict[str, Any]],
    facade: ExternalPluginFacadeDeps,
) -> PrivateNativeCallDeps:
    return PrivateNativeCallDeps(
        safe_str=facade.safe_str,
        runtime_allowed=facade.runtime_allowed,
        execute_native=execute_native,
    )


def build_self_thought_external_plugin_deps(
    facade: ExternalPluginFacadeDeps,
) -> SelfThoughtExternalPluginDeps:
    return SelfThoughtExternalPluginDeps(
        as_bool=facade.as_bool,
        safe_str=facade.safe_str,
        runtime_allowed=facade.runtime_allowed,
        prepare_call=facade.prepare_call,
        execute_http=facade.execute_http,
        read_text=read_text_safe,
        state_field=state_field,
        append_jsonl=append_external_plugin_trace,
        timestamp_or_now_iso=timestamp_or_now_iso,
    )


__all__ = [
    "ExternalPluginFacadeDeps",
    "build_admin_route_deps",
    "build_external_plugin_context",
    "build_external_plugin_call_deps",
    "build_private_native_call_deps",
    "build_private_native_execute_deps",
    "build_self_thought_external_plugin_deps",
    "external_plugin_summary",
]
