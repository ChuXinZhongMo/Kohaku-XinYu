from __future__ import annotations

from typing import Any, Awaitable, Callable, NamedTuple

from xinyu_bridge_turn_finish_memory_service import MemoryFinishResult
from xinyu_bridge_turn_finish_post_reply_service import PostReplyFinishResult


class DeliveryFinishResult(NamedTuple):
    proactive_owner_reply_marked: bool
    promised_followup: dict[str, Any]
    sticker_reply: dict[str, Any]
    sticker_tail_recorded: bool
    turn_coherence: dict[str, Any]


async def run_delivery_action_coherence_segments(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session: Any,
    session_key: str,
    turn_id: str,
    before_memory: dict[str, Any],
    final_guard_flags: list[str],
    private_thought_outcome: dict[str, Any],
    emotion_council: dict[str, Any],
    persona_sidecar: dict[str, Any],
    continuity_handoff: dict[str, Any],
    recalled_context_notes: list[str],
    self_code_task: str,
    direct_codex_task: str,
    model_codex_task: str,
    wait_to_think_task: str,
    model_codex_delegate_note: str,
    post_reply: PostReplyFinishResult,
    memory: MemoryFinishResult,
    schedule_promised_followup_func: Callable[..., dict[str, Any]],
    maybe_enqueue_sticker_reply_func: Callable[..., Awaitable[dict[str, Any]]],
    turn_action_result_func: Callable[..., str],
    finish_turn_coherence_func: Callable[..., dict[str, Any]],
) -> DeliveryFinishResult:
    runtime._append_dialogue_tail(session, user_text=text, reply=reply, payload=payload)
    proactive_owner_reply_marked = runtime._mark_proactive_owner_reply(payload, text=text, reply=reply)
    if proactive_owner_reply_marked:
        await runtime._desktop_publish_proactive_delivery_from_state(
            status_override="answered",
            notes=["owner_replied_to_proactive"],
        )
    promised_followup = schedule_promised_followup_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
        model_codex_task=bool(self_code_task or model_codex_task or direct_codex_task),
    )
    sticker_reply = await maybe_enqueue_sticker_reply_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
    )
    sticker_tail_recorded = runtime._append_sticker_delivery_tail(session, sticker_reply)
    action_result = turn_action_result_func(
        self_code_task=self_code_task,
        direct_codex_task=direct_codex_task,
        model_codex_task=model_codex_task,
        wait_to_think_task=wait_to_think_task,
        model_codex_delegate_note=model_codex_delegate_note,
        promised_followup=promised_followup,
        sticker_tail_recorded=sticker_tail_recorded,
    )
    turn_coherence = finish_turn_coherence_func(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        turn_id=turn_id,
        action_result=action_result,
        before_memory=before_memory,
        final_guard_flags=final_guard_flags,
        private_thought_outcome=private_thought_outcome,
        private_thought_link=post_reply.private_thought_link,
        emotion_council=emotion_council,
        persona_sidecar=persona_sidecar,
        candidate_result=memory.candidate_result,
        memory_self_review=memory.memory_self_review,
        recalled_context_notes=recalled_context_notes,
        continuity_handoff=continuity_handoff,
        interaction_journal=memory.interaction_journal,
        learning_closed_loop=post_reply.learning_closed_loop,
        uncertainty_pause=post_reply.uncertainty_pause,
        promised_followup=promised_followup,
        sticker_reply=sticker_reply,
    )
    return DeliveryFinishResult(
        proactive_owner_reply_marked=proactive_owner_reply_marked,
        promised_followup=promised_followup,
        sticker_reply=sticker_reply,
        sticker_tail_recorded=sticker_tail_recorded,
        turn_coherence=turn_coherence,
    )
