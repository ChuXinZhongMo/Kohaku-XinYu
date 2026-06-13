from __future__ import annotations

from typing import Any

from xinyu_bridge_turn_finish_delivery_service import run_delivery_action_coherence_segments
from xinyu_bridge_turn_finish_memory_service import run_memory_archive_finish_sidecars
from xinyu_bridge_turn_finish_post_reply_service import run_post_reply_finish_sidecars
from xinyu_bridge_turn_finish_result import build_slow_turn_finish_sidecars_result
from xinyu_bridge_turn_finish_service_deps import TurnFinishServiceDeps


async def run_slow_turn_finish_sidecars(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    draft_reply: str,
    session: Any,
    session_key: str,
    turn_id: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    visible_turn: Any,
    final_guard_flags: list[str],
    expression_learning: dict[str, Any],
    recalled_context: Any,
    recalled_context_notes: list[str],
    private_thought_outcome: dict[str, Any],
    emotion_council: dict[str, Any],
    persona_sidecar: dict[str, Any],
    continuity_handoff: dict[str, Any],
    wait_to_think_sidecar: dict[str, Any],
    self_code_task: str,
    direct_codex_task: str,
    model_codex_task: str,
    wait_to_think_task: str,
    model_codex_delegate_note: str,
    deps: TurnFinishServiceDeps,
) -> dict[str, Any]:
    post_reply = run_post_reply_finish_sidecars(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        draft_reply=draft_reply,
        session_key=session_key,
        visible_turn=visible_turn,
        final_guard_flags=final_guard_flags,
        expression_learning=expression_learning,
        recalled_context=recalled_context,
        record_uncertainty_pause_func=deps.record_uncertainty_pause,
        observe_post_reply_self_observation_func=deps.observe_post_reply_self_observation,
        record_learning_closed_loop_func=deps.record_learning_closed_loop,
        write_turn_residue_func=deps.write_turn_residue,
        record_owner_voice_sidecars_func=deps.record_owner_voice_sidecars,
        record_curiosity_prediction_func=deps.record_curiosity_prediction,
        record_private_thought_link_func=deps.record_private_thought_link,
    )
    memory = run_memory_archive_finish_sidecars(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session=session,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_at=turn_started_at,
        visible_turn=visible_turn,
        final_guard_flags=final_guard_flags,
        recalled_context=recalled_context,
        recalled_context_notes=recalled_context_notes,
        post_reply_observation=post_reply.post_reply_observation,
        archive_dialogue_turn_func=deps.archive_dialogue_turn,
        log_living_memory_recall_func=deps.log_living_memory_recall,
        extract_memory_candidates_func=deps.extract_memory_candidates,
        run_memory_self_review_func=deps.run_memory_self_review,
        record_interaction_journal_func=deps.record_interaction_journal,
    )
    delivery = await run_delivery_action_coherence_segments(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session=session,
        session_key=session_key,
        turn_id=turn_id,
        before_memory=before_memory,
        final_guard_flags=final_guard_flags,
        private_thought_outcome=private_thought_outcome,
        emotion_council=emotion_council,
        persona_sidecar=persona_sidecar,
        continuity_handoff=continuity_handoff,
        recalled_context_notes=recalled_context_notes,
        self_code_task=self_code_task,
        direct_codex_task=direct_codex_task,
        model_codex_task=model_codex_task,
        wait_to_think_task=wait_to_think_task,
        model_codex_delegate_note=model_codex_delegate_note,
        post_reply=post_reply,
        memory=memory,
        schedule_promised_followup_func=deps.schedule_promised_followup,
        maybe_enqueue_sticker_reply_func=deps.maybe_enqueue_sticker_reply,
        turn_action_result_func=deps.turn_action_result,
        finish_turn_coherence_func=deps.finish_turn_coherence,
    )

    return build_slow_turn_finish_sidecars_result(
        post_reply=post_reply,
        memory=memory,
        delivery=delivery,
        after_memory=deps.memory_snapshot(runtime.memory_root),
    )
