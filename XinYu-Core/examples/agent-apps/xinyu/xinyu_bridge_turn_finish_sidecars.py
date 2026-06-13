from __future__ import annotations

import asyncio
import time
from typing import Any

from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
import xinyu_bridge_turn_finish_delivery_bindings as _delivery_bindings
from xinyu_bridge_turn_finish_delivery import (
    finish_turn_coherence_sidecar as _runtime_finish_turn_coherence,
    maybe_enqueue_sticker_reply_sidecar as _runtime_maybe_enqueue_sticker_reply,
    schedule_promised_followup_sidecar as _runtime_schedule_promised_followup,
    turn_action_result as _runtime_turn_action_result,
)
import xinyu_bridge_turn_finish_memory_bindings as _memory_bindings
from xinyu_bridge_turn_finish_memory import (
    archive_dialogue_turn_sidecar as _runtime_archive_dialogue_turn,
    extract_memory_candidates_sidecar as _runtime_extract_memory_candidates,
    record_interaction_journal_sidecar as _runtime_record_interaction_journal,
    run_memory_self_review_sidecar as _runtime_run_memory_self_review,
)
import xinyu_bridge_turn_finish_post_reply_bindings as _post_reply_bindings
from xinyu_bridge_turn_finish_post_reply import (
    observe_post_reply_self_observation_sidecar as _runtime_observe_post_reply_self_observation,
    record_curiosity_prediction_sidecar as _runtime_record_curiosity_prediction,
    record_learning_closed_loop_sidecar as _runtime_record_learning_closed_loop,
    record_owner_voice_sidecars as _runtime_record_owner_voice_sidecars,
    record_private_thought_link_sidecar as _runtime_record_private_thought_link,
    record_uncertainty_pause_sidecar as _runtime_record_uncertainty_pause,
)
from xinyu_bridge_turn_finish_service import run_slow_turn_finish_sidecars as _runtime_run_slow_turn_finish_sidecars
from xinyu_bridge_turn_finish_service_deps import TurnFinishServiceDeps
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_dialogue_archive import archive_dialogue_turn
from xinyu_dialogue_curiosity import record_reply_prediction
from xinyu_interaction_journal import record_interaction_turn
from xinyu_learning_closed_loop import record_learning_closed_loop_turn
from xinyu_living_memory_recall import log_living_memory_recall
from xinyu_memory_candidate_extractor import extract_memory_candidates
from xinyu_memory_candidate_maintenance import run_memory_candidate_maintenance
from xinyu_memory_self_review import run_memory_self_review
from xinyu_post_reply_self_observation import observe_post_reply_self_observation
from xinyu_private_thought_events import record_private_thought_reply_link
from xinyu_recent_context_guard import ensure_recent_context_health
from xinyu_sticker_pack import maybe_enqueue_sticker_reply
from xinyu_turn_coherence import finish_turn_coherence
from xinyu_turn_residue import write_turn_residue
from xinyu_uncertainty_pause import is_waiting_reply, record_uncertainty_pause
from xinyu_voice_learning import record_voice_correction
from xinyu_voice_trial_overlay import record_voice_trial_overlay


def _facade_globals() -> dict[str, Any]:
    return globals()


_record_uncertainty_pause = _post_reply_bindings.bind_record_uncertainty_pause(_facade_globals)
_observe_post_reply_self_observation = _post_reply_bindings.bind_observe_post_reply_self_observation(_facade_globals)
_record_learning_closed_loop = _post_reply_bindings.bind_record_learning_closed_loop(_facade_globals)
_record_owner_voice_sidecars = _post_reply_bindings.bind_record_owner_voice_sidecars(_facade_globals)
_record_curiosity_prediction = _post_reply_bindings.bind_record_curiosity_prediction(_facade_globals)
_record_private_thought_link = _post_reply_bindings.bind_record_private_thought_link(_facade_globals)
_archive_dialogue_turn = _memory_bindings.bind_archive_dialogue_turn(_facade_globals)
_extract_memory_candidates = _memory_bindings.bind_extract_memory_candidates(_facade_globals)
_run_memory_self_review = _memory_bindings.bind_run_memory_self_review(_facade_globals)
_record_interaction_journal = _memory_bindings.bind_record_interaction_journal(_facade_globals)
_schedule_promised_followup = _delivery_bindings.bind_schedule_promised_followup(_facade_globals)
_maybe_enqueue_sticker_reply = _delivery_bindings.bind_maybe_enqueue_sticker_reply(_facade_globals)
_turn_action_result = _delivery_bindings.bind_turn_action_result(_facade_globals)
_finish_turn_coherence = _delivery_bindings.bind_finish_turn_coherence(_facade_globals)


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
) -> dict[str, Any]:
    return await _runtime_run_slow_turn_finish_sidecars(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        draft_reply=draft_reply,
        session=session,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        visible_turn=visible_turn,
        final_guard_flags=final_guard_flags,
        expression_learning=expression_learning,
        recalled_context=recalled_context,
        recalled_context_notes=recalled_context_notes,
        private_thought_outcome=private_thought_outcome,
        emotion_council=emotion_council,
        persona_sidecar=persona_sidecar,
        continuity_handoff=continuity_handoff,
        wait_to_think_sidecar=wait_to_think_sidecar,
        self_code_task=self_code_task,
        direct_codex_task=direct_codex_task,
        model_codex_task=model_codex_task,
        wait_to_think_task=wait_to_think_task,
        model_codex_delegate_note=model_codex_delegate_note,
        deps=TurnFinishServiceDeps(
            record_uncertainty_pause=_record_uncertainty_pause,
            observe_post_reply_self_observation=_observe_post_reply_self_observation,
            record_learning_closed_loop=_record_learning_closed_loop,
            write_turn_residue=write_turn_residue,
            record_owner_voice_sidecars=_record_owner_voice_sidecars,
            record_curiosity_prediction=_record_curiosity_prediction,
            record_private_thought_link=_record_private_thought_link,
            archive_dialogue_turn=_archive_dialogue_turn,
            log_living_memory_recall=log_living_memory_recall,
            extract_memory_candidates=_extract_memory_candidates,
            run_memory_self_review=_run_memory_self_review,
            record_interaction_journal=_record_interaction_journal,
            schedule_promised_followup=_schedule_promised_followup,
            maybe_enqueue_sticker_reply=_maybe_enqueue_sticker_reply,
            turn_action_result=_turn_action_result,
            finish_turn_coherence=_finish_turn_coherence,
            memory_snapshot=_memory_snapshot,
        ),
    )
