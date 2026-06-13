from __future__ import annotations

from datetime import datetime
from http import HTTPStatus
from typing import Any

import xinyu_bridge_desktop_self_action_approval as self_action_approval
import xinyu_bridge_desktop_self_action_labels as self_action_labels
from xinyu_bridge_desktop_self_action_approval_backend import (
    attach_in_process_desktop_self_action_patch_executor,
    compose_in_process_desktop_self_action_approval_reply,
    execute_desktop_self_action_approval,
    resolve_in_process_desktop_self_action_pending_item,
)
from xinyu_bridge_desktop_surface_route_backend import maybe_execute_desktop_surface_backend
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import compact_text as _compact_text
from xinyu_bridge_values import safe_str as _safe_str


async def desktop_self_action_approval(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if runtime._closed:
        raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
    backend_result = await maybe_execute_desktop_surface_backend(
        runtime,
        payload,
        route="/desktop/self-action/approval",
        http_method="POST",
        runtime_method="desktop_self_action_approval",
    )
    if backend_result is not None:
        return backend_result
    request = self_action_approval.parse_desktop_self_action_approval_payload(
        payload,
        request_error_type=BridgeRequestError,
        bad_request_status=HTTPStatus.BAD_REQUEST,
        safe_str_func=_safe_str,
        as_bool_func=_as_bool,
    )
    checked_at = datetime.now().astimezone().isoformat()
    return await execute_desktop_self_action_approval(runtime, request, checked_at=checked_at)


async def desktop_attach_self_action_patch_executor(
    runtime: Any,
    result: dict[str, Any],
    *,
    checked_at: str,
    authorize_codex: bool,
    timeout_seconds: int,
) -> None:
    await attach_in_process_desktop_self_action_patch_executor(
        runtime,
        result,
        checked_at=checked_at,
        authorize_codex=authorize_codex,
        timeout_seconds=timeout_seconds,
    )


def desktop_self_action_pending_item(runtime: Any, queue_id: str) -> dict[str, Any]:
    return resolve_in_process_desktop_self_action_pending_item(runtime, queue_id)


def desktop_self_action_approval_reply(result: dict[str, Any], *, decision: str) -> str:
    return compose_in_process_desktop_self_action_approval_reply(result, decision=decision)


def self_action_goal_label(goal_id: str) -> str:
    return self_action_labels.self_action_goal_label(goal_id, safe_str_func=_safe_str)


def self_action_action_label(action_kind: str) -> str:
    return self_action_labels.self_action_action_label(action_kind, safe_str_func=_safe_str)


def self_action_intent_label(action_kind: str, goal_id: str, item: dict[str, Any]) -> str:
    return self_action_labels.self_action_intent_label(
        action_kind,
        goal_id,
        item,
        safe_str_func=_safe_str,
        compact_text_func=_compact_text,
        goal_label_func=self_action_goal_label,
        action_label_func=self_action_action_label,
    )


def self_action_reason_label(action_kind: str, goal_id: str, item: dict[str, Any]) -> str:
    return self_action_labels.self_action_reason_label(
        action_kind,
        goal_id,
        item,
        safe_str_func=_safe_str,
        compact_text_func=_compact_text,
    )


def self_action_scope_label(approval_scope: str, action_kind: str) -> str:
    return self_action_labels.self_action_scope_label(approval_scope, action_kind, safe_str_func=_safe_str)


def self_action_boundary_label(action_kind: str) -> str:
    return self_action_labels.self_action_boundary_label(action_kind)


def self_action_approval_effect_label(action_kind: str) -> str:
    return self_action_labels.self_action_approval_effect_label(action_kind)


def self_action_ecology_context_label(goal_id: str, approval_scope: str) -> str:
    return self_action_labels.self_action_ecology_context_label(
        goal_id,
        approval_scope,
        safe_str_func=_safe_str,
        goal_label_func=self_action_goal_label,
    )


def self_action_patch_goal_label(goal_id: str, approval_scope: str) -> str:
    return self_action_labels.self_action_patch_goal_label(goal_id, approval_scope)
