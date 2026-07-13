from __future__ import annotations

from typing import Any

from xinyu_bridge_codex_owner_direct_policy import owner_direct_codex_task
from xinyu_bridge_codex_policy_self_code import (
    owner_self_code_direct_grant_requested_impl,
    owner_self_code_iteration_task_impl,
    recent_owner_self_code_grant_impl,
)
from xinyu_bridge_codex_policy_markers import (
    OWNER_DIRECT_CODEX_DELEGATE_MARKERS,
    OWNER_DIRECT_CODEX_NEGATIVE_MARKERS,
    OWNER_DIRECT_CODEX_SUPPORT_MARKERS,
    OWNER_SELF_CODE_EDIT_GRANT_MARKERS,
    OWNER_SELF_CODE_GRANT_CUES,
    OWNER_SELF_CODE_NEGATIVE_MARKERS,
    OWNER_SELF_CODE_START_MARKERS,
)
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_bridge_values import safe_str
from xinyu_codex_delegate import looks_like_codex_request
from xinyu_dialogue_working_memory import load_dialogue_tail
from xinyu_self_code_approval import consume_self_code_approval, create_direct_self_code_approval
from xinyu_text_variants import readable_markers


def _deps() -> dict[str, Any]:
    return globals()


def owner_self_code_grant_in_text(
    runtime: Any,
    compact_text: str,
    *,
    negative_markers: tuple[str, ...] = OWNER_SELF_CODE_NEGATIVE_MARKERS,
    edit_grant_markers: tuple[str, ...] = OWNER_SELF_CODE_EDIT_GRANT_MARKERS,
    grant_cues: tuple[str, ...] = OWNER_SELF_CODE_GRANT_CUES,
) -> bool:
    del runtime
    if any(marker in compact_text for marker in negative_markers):
        return False
    if not any(marker in compact_text for marker in edit_grant_markers):
        return False
    if any(marker in compact_text for marker in grant_cues):
        return True
    return any(
        marker in compact_text
        for marker in (
            "主动改代码",
            "主动修改代码",
            "主动更改代码",
            "开始改代码",
            "直接改代码",
        )
    )


def recent_owner_self_code_grant(
    runtime: Any,
    session_key: str,
    *,
    negative_markers: tuple[str, ...] = OWNER_SELF_CODE_NEGATIVE_MARKERS,
    edit_grant_markers: tuple[str, ...] = OWNER_SELF_CODE_EDIT_GRANT_MARKERS,
    grant_cues: tuple[str, ...] = OWNER_SELF_CODE_GRANT_CUES,
) -> bool:
    return recent_owner_self_code_grant_impl(
        runtime,
        session_key,
        negative_markers=negative_markers,
        edit_grant_markers=edit_grant_markers,
        grant_cues=grant_cues,
        deps=_deps(),
    )


def owner_self_code_direct_grant_requested(
    runtime: Any,
    user_text: str,
    *,
    session_key: str,
    negative_markers: tuple[str, ...] = OWNER_SELF_CODE_NEGATIVE_MARKERS,
    edit_grant_markers: tuple[str, ...] = OWNER_SELF_CODE_EDIT_GRANT_MARKERS,
    start_markers: tuple[str, ...] = OWNER_SELF_CODE_START_MARKERS,
    grant_cues: tuple[str, ...] = OWNER_SELF_CODE_GRANT_CUES,
) -> bool:
    return owner_self_code_direct_grant_requested_impl(
        runtime,
        user_text,
        session_key=session_key,
        negative_markers=negative_markers,
        edit_grant_markers=edit_grant_markers,
        start_markers=start_markers,
        grant_cues=grant_cues,
        deps=_deps(),
    )


def owner_self_code_iteration_task(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    negative_markers: tuple[str, ...] = OWNER_SELF_CODE_NEGATIVE_MARKERS,
    edit_grant_markers: tuple[str, ...] = OWNER_SELF_CODE_EDIT_GRANT_MARKERS,
    start_markers: tuple[str, ...] = OWNER_SELF_CODE_START_MARKERS,
    grant_cues: tuple[str, ...] = OWNER_SELF_CODE_GRANT_CUES,
) -> str:
    return owner_self_code_iteration_task_impl(
        runtime,
        payload,
        user_text=user_text,
        reply=reply,
        session_key=session_key,
        negative_markers=negative_markers,
        edit_grant_markers=edit_grant_markers,
        start_markers=start_markers,
        grant_cues=grant_cues,
        deps=_deps(),
    )

__all__ = (
    "Any",
    "OWNER_DIRECT_CODEX_DELEGATE_MARKERS",
    "OWNER_DIRECT_CODEX_NEGATIVE_MARKERS",
    "OWNER_DIRECT_CODEX_SUPPORT_MARKERS",
    "OWNER_SELF_CODE_EDIT_GRANT_MARKERS",
    "OWNER_SELF_CODE_GRANT_CUES",
    "OWNER_SELF_CODE_NEGATIVE_MARKERS",
    "OWNER_SELF_CODE_START_MARKERS",
    "_deps",
    "annotations",
    "consume_self_code_approval",
    "create_direct_self_code_approval",
    "load_dialogue_tail",
    "looks_like_codex_request",
    "normalize_bridge_reply",
    "owner_direct_codex_task",
    "owner_self_code_direct_grant_requested",
    "owner_self_code_direct_grant_requested_impl",
    "owner_self_code_grant_in_text",
    "owner_self_code_iteration_task",
    "owner_self_code_iteration_task_impl",
    "readable_markers",
    "recent_owner_self_code_grant",
    "recent_owner_self_code_grant_impl",
    "safe_str",
)
