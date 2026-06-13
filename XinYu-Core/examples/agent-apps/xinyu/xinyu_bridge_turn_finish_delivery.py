from __future__ import annotations

from datetime import datetime
from typing import Any, Awaitable, Callable


def schedule_promised_followup_sidecar(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session_key: str,
    model_codex_task: bool,
) -> dict[str, Any]:
    try:
        return runtime._schedule_promised_followup_if_needed(
            payload,
            user_text=text,
            reply=reply,
            session_key=session_key,
            model_codex_task=model_codex_task,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] promised followup scheduling failed: {exc}", flush=True)
        return {"notes": [f"promised_followup_error:{type(exc).__name__}"]}


async def maybe_enqueue_sticker_reply_sidecar(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session_key: str,
    turn_id: str,
    maybe_enqueue_sticker_reply_func: Callable[..., dict[str, Any]],
    to_thread_func: Callable[..., Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    try:
        return await to_thread_func(
            maybe_enqueue_sticker_reply_func,
            runtime.xinyu_dir,
            payload,
            user_text=text,
            reply=reply,
            session_key=session_key,
            turn_id=turn_id,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] sticker reply enqueue failed: {exc}", flush=True)
        return {"notes": [f"sticker_reply_error:{type(exc).__name__}"]}


def turn_action_result(
    *,
    self_code_task: str,
    direct_codex_task: str,
    model_codex_task: str,
    wait_to_think_task: str,
    model_codex_delegate_note: str,
    promised_followup: dict[str, Any],
    sticker_tail_recorded: bool,
) -> str:
    if self_code_task:
        return model_codex_delegate_note or "self_code_iteration_considered"
    if direct_codex_task:
        return model_codex_delegate_note or "owner_direct_codex_considered"
    if model_codex_task:
        return model_codex_delegate_note or "model_codex_delegate_considered"
    if wait_to_think_task:
        return "wait_to_think_scheduled"
    if promised_followup.get("scheduled"):
        return "promised_followup_scheduled"
    if sticker_tail_recorded:
        return "sticker_reply_enqueued"
    return "none"


def finish_turn_coherence_sidecar(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    turn_id: str,
    action_result: str,
    before_memory: dict[str, Any],
    final_guard_flags: list[str],
    private_thought_outcome: dict[str, Any],
    private_thought_link: dict[str, Any],
    emotion_council: dict[str, Any],
    persona_sidecar: dict[str, Any],
    candidate_result: dict[str, Any],
    memory_self_review: dict[str, Any],
    recalled_context_notes: list[str],
    continuity_handoff: dict[str, Any],
    interaction_journal: dict[str, Any],
    learning_closed_loop: dict[str, Any],
    uncertainty_pause: dict[str, Any],
    promised_followup: dict[str, Any],
    sticker_reply: dict[str, Any],
    finish_turn_coherence_func: Callable[..., dict[str, Any]],
    memory_snapshot_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    try:
        return finish_turn_coherence_func(
            runtime.xinyu_dir,
            turn_id=turn_id,
            payload=payload,
            user_text=text,
            reply=reply,
            action_result=action_result,
            memory_changed=before_memory != memory_snapshot_func(runtime.memory_root),
            final_guard_flags=final_guard_flags,
            component_notes={
                "private_thought_outcome": private_thought_outcome,
                "private_thought_link": private_thought_link,
                "emotion_council": emotion_council,
                "persona_sidecar": persona_sidecar,
                "memory_candidate": candidate_result,
                "memory_self_review": memory_self_review,
                "context_recall": recalled_context_notes,
                "continuity_handoff": continuity_handoff,
                "interaction_journal": interaction_journal,
                "learning_closed_loop": learning_closed_loop,
                "uncertainty_pause": uncertainty_pause,
                "promised_followup": promised_followup,
                "sticker_reply": sticker_reply,
            },
            checked_at=datetime.now().astimezone().isoformat(),
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] turn coherence finish failed: {exc}", flush=True)
        return {"notes": [f"turn_coherence_error:{type(exc).__name__}"]}
