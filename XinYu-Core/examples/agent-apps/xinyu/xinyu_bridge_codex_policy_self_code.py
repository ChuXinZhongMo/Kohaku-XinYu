from __future__ import annotations

from typing import Any, Mapping


def recent_owner_self_code_grant_impl(
    runtime: Any,
    session_key: str,
    *,
    negative_markers: tuple[str, ...],
    edit_grant_markers: tuple[str, ...],
    grant_cues: tuple[str, ...],
    deps: Mapping[str, Any],
) -> bool:
    tail = deps["load_dialogue_tail"](runtime.xinyu_dir, session_key, max_entries=8)
    for item in reversed(tail):
        if item.get("role") != "user":
            continue
        compact = runtime._compact_promise_text(item.get("content", ""))
        if any(marker in compact for marker in negative_markers):
            return False
        if deps["owner_self_code_grant_in_text"](
            runtime,
            compact,
            negative_markers=negative_markers,
            edit_grant_markers=edit_grant_markers,
            grant_cues=grant_cues,
        ):
            return True
    return False


def owner_self_code_direct_grant_requested_impl(
    runtime: Any,
    user_text: str,
    *,
    session_key: str,
    negative_markers: tuple[str, ...],
    edit_grant_markers: tuple[str, ...],
    start_markers: tuple[str, ...],
    grant_cues: tuple[str, ...],
    deps: Mapping[str, Any],
) -> bool:
    compact_user = runtime._compact_promise_text(user_text)
    if any(marker in compact_user for marker in negative_markers):
        return False
    if deps["owner_self_code_grant_in_text"](
        runtime,
        compact_user,
        negative_markers=negative_markers,
        edit_grant_markers=edit_grant_markers,
        grant_cues=grant_cues,
    ):
        return True
    has_start_marker = any(marker in compact_user for marker in start_markers)
    return has_start_marker and deps["recent_owner_self_code_grant"](
        runtime,
        session_key,
        negative_markers=negative_markers,
        edit_grant_markers=edit_grant_markers,
        grant_cues=grant_cues,
    )


def owner_self_code_iteration_task_impl(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    negative_markers: tuple[str, ...],
    edit_grant_markers: tuple[str, ...],
    start_markers: tuple[str, ...],
    grant_cues: tuple[str, ...],
    deps: Mapping[str, Any],
) -> str:
    if not runtime._can_model_delegate_codex(payload):
        return ""
    approval = deps["consume_self_code_approval"](
        runtime.xinyu_dir,
        payload,
        owner_text=user_text,
        session_key=session_key,
        reply=reply,
    )
    if approval.get("approved"):
        approval_reason = (
            "The approval exists because XinYu first sent a QQ self-code application and owner approved "
            "that pending request."
        )
    else:
        if not deps["owner_self_code_direct_grant_requested"](
            runtime,
            user_text,
            session_key=session_key,
            negative_markers=negative_markers,
            edit_grant_markers=edit_grant_markers,
            start_markers=start_markers,
            grant_cues=grant_cues,
        ):
            return ""
        approval = deps["create_direct_self_code_approval"](
            runtime.xinyu_dir,
            payload,
            owner_text=user_text,
            session_key=session_key,
            reply=reply,
        )
        if not approval.get("approved"):
            return ""
        approval_reason = (
            "The approval exists because the owner directly requested or authorized self-code modification "
            "in QQ private chat."
        )
    return deps["normalize_bridge_reply"](
        "\n".join(
            [
                f"Self-code approval id: {deps['safe_str'](approval.get('approval_id'), 'unknown')}",
                approval_reason,
                deps["safe_str"](approval.get("task_text")),
            ]
        )
    )
