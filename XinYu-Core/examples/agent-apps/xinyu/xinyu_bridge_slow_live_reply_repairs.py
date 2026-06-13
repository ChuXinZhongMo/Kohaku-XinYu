from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_human_voice_flags import regen_pipeline_enabled


def apply_stale_context_repair(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
    final_guard_flags: list[str],
    blocked_by_delegate: bool,
    owner_private_match_func: Callable[..., bool],
    stale_reply_func: Callable[[str], bool],
    repair_reply_func: Callable[..., str],
    normalize_func: Callable[[str], str],
    dedupe_func: Callable[[list[str]], list[str]],
) -> dict[str, Any]:
    unchanged_result = {
        "reply": reply,
        "final_guard_flags": final_guard_flags,
        "stale_context_reply_replaced": False,
    }
    if not owner_private_match_func(runtime, payload) or blocked_by_delegate:
        return unchanged_result

    if not stale_reply_func(reply):
        return unchanged_result

    if regen_pipeline_enabled():
        # plan §5 阶段4: drop the stale model line and clear it so the
        # model-first empty-recovery step regenerates a fresh current-turn reply
        # instead of swapping in the canned repair constant.
        final_guard_flags = dedupe_func(
            list(final_guard_flags or []) + ["stale_context_reply_replaced", "stale_context_regen_pending"]
        )
        runtime._replace_last_assistant_message(session.agent, "")
        return {
            "reply": "",
            "final_guard_flags": final_guard_flags,
            "stale_context_reply_replaced": True,
        }

    repair_reply = repair_reply_func(runtime, user_text)
    if not repair_reply:
        return unchanged_result

    reply = normalize_func(repair_reply)
    final_guard_flags = dedupe_func(list(final_guard_flags or []) + ["stale_context_reply_replaced"])
    runtime._replace_last_assistant_message(session.agent, reply)
    return {
        "reply": reply,
        "final_guard_flags": final_guard_flags,
        "stale_context_reply_replaced": True,
    }


def apply_current_reference_repair(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    user_text: str,
    final_guard_flags: list[str],
    blocked_by_delegate: bool,
    owner_private_match_func: Callable[..., bool],
    repair_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
    dedupe_func: Callable[[list[str]], list[str]],
) -> dict[str, Any]:
    current_reference_repair: dict[str, Any] = {"changed": False, "reply": reply, "notes": []}
    if not owner_private_match_func(runtime, payload) or blocked_by_delegate:
        return {
            "reply": reply,
            "final_guard_flags": final_guard_flags,
            "current_reference_repair": current_reference_repair,
        }

    current_reference_repair = repair_func(
        user_text=user_text,
        reply=reply,
        dialogue_tail=session.dialogue_tail,
    )
    if current_reference_repair.get("changed"):
        reply = safe_str_func(current_reference_repair.get("reply")).strip()
        final_guard_flags = dedupe_func(
            list(final_guard_flags or [])
            + [str(note) for note in current_reference_repair.get("notes", []) if str(note)]
        )
        runtime._replace_last_assistant_message(session.agent, reply)
    return {
        "reply": reply,
        "final_guard_flags": final_guard_flags,
        "current_reference_repair": current_reference_repair,
    }
