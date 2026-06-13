from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from xinyu_external_plugins import ExternalCallContext


@dataclass(frozen=True)
class PrivateNativeExecuteDeps:
    safe_str: Callable[..., str]
    as_int: Callable[..., int]


@dataclass(frozen=True)
class PrivateNativeCallDeps:
    safe_str: Callable[..., str]
    runtime_allowed: Callable[..., tuple[bool, str, dict[str, Any]]]
    execute_native: Callable[[Any, str, str, dict[str, Any], ExternalCallContext], dict[str, Any]]


def execute_private_ecosystem_native_impl(
    root: Any,
    plugin_id: str,
    capability: str,
    args: dict[str, Any],
    context: ExternalCallContext,
    deps: PrivateNativeExecuteDeps,
) -> dict[str, Any]:
    from xinyu_private_ecosystem_grants import load_grants

    grants = load_grants(root)
    if plugin_id == "xinyu_private_desktop":
        from xinyu_bridge_external_plugin_native_desktop import execute_private_desktop

        return execute_private_desktop(root, capability, args, context, grants, deps)
    if plugin_id == "xinyu_private_browser":
        from xinyu_bridge_external_plugin_native_browser import execute_private_browser

        return execute_private_browser(root, capability, args, context, grants, deps)
    from xinyu_bridge_external_plugin_native_computer import execute_computer_control

    return execute_computer_control(root, capability, args, context, grants, deps)


def run_private_ecosystem_native_call_impl(
    root: Any,
    plugin_id: str,
    capability: str,
    args: dict[str, Any],
    context: ExternalCallContext,
    *,
    execute: bool,
    deps: PrivateNativeCallDeps,
) -> dict[str, Any]:
    from xinyu_external_plugins import default_external_plugins, evaluate_external_call

    allowed, reason, _plugin_state = deps.runtime_allowed(root, plugin_id, proactive=context.proactive)
    if not allowed:
        return {"ok": False, "blocked": True, "reason": reason, "result": "blocked", "decision": {}, "execution": {}}

    decision = evaluate_external_call(default_external_plugins(), plugin_id, capability, context)
    if not decision.ok:
        return {
            "ok": False,
            "blocked": True,
            "reason": decision.reason,
            "result": "blocked",
            "decision": decision.to_dict(),
            "execution": {},
        }
    if not execute:
        return {
            "ok": True,
            "blocked": False,
            "reason": "prepared",
            "result": "prepared",
            "decision": decision.to_dict(),
            "execution": {},
        }

    execution = deps.execute_native(root, plugin_id, capability, args, context)
    ok = bool(execution.get("ok"))
    return {
        "ok": ok,
        "blocked": not ok,
        "reason": deps.safe_str(execution.get("error_code")) or ("ok" if ok else "blocked"),
        "result": deps.safe_str(execution.get("result")),
        "decision": decision.to_dict(),
        "execution": execution,
    }
