from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any

from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_bridge_values import as_bool as _as_bool
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
    uncertainty_pause = _record_uncertainty_pause(
        runtime,
        payload=payload,
        text=text,
        draft_reply=draft_reply,
        reply=reply,
        final_guard_flags=final_guard_flags,
        session_key=session_key,
        visible_turn=visible_turn,
    )
    post_reply_observation = _observe_post_reply_self_observation(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        visible_turn=visible_turn,
        final_guard_flags=final_guard_flags,
        expression_learning=expression_learning,
        recalled_context=recalled_context,
    )
    learning_closed_loop = _record_learning_closed_loop(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
        visible_turn=visible_turn,
        final_guard_flags=final_guard_flags,
        expression_learning=expression_learning,
        post_reply_observation=post_reply_observation,
    )
    residue_written = write_turn_residue(
        runtime.xinyu_dir,
        scene=runtime.speech_controller.classify(payload=payload, user_text=text),
        user_text=text,
        reply=reply,
        source="qq_gateway",
    )
    voice_trial_overlay, voice_calibrated = _record_owner_voice_sidecars(runtime, payload=payload, text=text, reply=reply)
    curiosity_prediction = _record_curiosity_prediction(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
    )
    private_thought_link = _record_private_thought_link(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
    )
    archive_result = _archive_dialogue_turn(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        visible_turn=visible_turn,
        final_guard_flags=final_guard_flags,
    )
    if recalled_context is not None and getattr(recalled_context, "items", ()):
        try:
            if log_living_memory_recall(runtime.xinyu_dir, recalled_context):
                recalled_context_notes.append("recalled_context_logged")
        except Exception as exc:
            print(f"[xinyu_core_bridge] recalled context log failed: {exc}", flush=True)
            recalled_context_notes.append(f"recalled_context_log_error:{type(exc).__name__}")

    candidate_result = _extract_memory_candidates(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        archive_result=archive_result,
        session=session,
        visible_turn=visible_turn,
        final_guard_flags=final_guard_flags,
        post_reply_observation=post_reply_observation,
    )
    memory_self_review = _run_memory_self_review(runtime)
    interaction_journal = _record_interaction_journal(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
        visible_turn=visible_turn,
        turn_id=turn_id,
        turn_started_at=turn_started_at,
    )
    runtime._append_dialogue_tail(session, user_text=text, reply=reply, payload=payload)
    proactive_owner_reply_marked = runtime._mark_proactive_owner_reply(payload, text=text, reply=reply)
    if proactive_owner_reply_marked:
        await runtime._desktop_publish_proactive_delivery_from_state(
            status_override="answered",
            notes=["owner_replied_to_proactive"],
        )
    promised_followup = _schedule_promised_followup(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
        model_codex_task=bool(self_code_task or model_codex_task or direct_codex_task),
    )
    sticker_reply = await _maybe_enqueue_sticker_reply(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
    )
    sticker_tail_recorded = runtime._append_sticker_delivery_tail(session, sticker_reply)
    action_result = _turn_action_result(
        self_code_task=self_code_task,
        direct_codex_task=direct_codex_task,
        model_codex_task=model_codex_task,
        wait_to_think_task=wait_to_think_task,
        model_codex_delegate_note=model_codex_delegate_note,
        promised_followup=promised_followup,
        sticker_tail_recorded=sticker_tail_recorded,
    )
    turn_coherence = _finish_turn_coherence(
        runtime,
        payload=payload,
        text=text,
        reply=reply,
        turn_id=turn_id,
        action_result=action_result,
        before_memory=before_memory,
        final_guard_flags=final_guard_flags,
        private_thought_outcome=private_thought_outcome,
        private_thought_link=private_thought_link,
        emotion_council=emotion_council,
        persona_sidecar=persona_sidecar,
        candidate_result=candidate_result,
        memory_self_review=memory_self_review,
        recalled_context_notes=recalled_context_notes,
        continuity_handoff=continuity_handoff,
        interaction_journal=interaction_journal,
        learning_closed_loop=learning_closed_loop,
        uncertainty_pause=uncertainty_pause,
        promised_followup=promised_followup,
        sticker_reply=sticker_reply,
    )

    return {
        "uncertainty_pause": uncertainty_pause,
        "post_reply_observation": post_reply_observation,
        "learning_closed_loop": learning_closed_loop,
        "residue_written": residue_written,
        "voice_calibrated": voice_calibrated,
        "voice_trial_overlay": voice_trial_overlay,
        "curiosity_prediction": curiosity_prediction,
        "private_thought_link": private_thought_link,
        "archive_result": archive_result,
        "candidate_result": candidate_result,
        "memory_self_review": memory_self_review,
        "interaction_journal": interaction_journal,
        "proactive_owner_reply_marked": proactive_owner_reply_marked,
        "promised_followup": promised_followup,
        "sticker_reply": sticker_reply,
        "sticker_tail_recorded": sticker_tail_recorded,
        "turn_coherence": turn_coherence,
        "after_memory": _memory_snapshot(runtime.memory_root),
    }


def _record_uncertainty_pause(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    draft_reply: str,
    reply: str,
    final_guard_flags: list[str],
    session_key: str,
    visible_turn: Any,
) -> dict[str, Any]:
    if not is_waiting_reply(reply) and "final_guard_blocked_unsendable_reply" not in final_guard_flags:
        return {"notes": []}
    reason = "waiting_marker" if is_waiting_reply(reply) else "final_guard_blocked_unsendable_reply"
    try:
        return record_uncertainty_pause(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            draft_reply=draft_reply,
            final_reply=reply,
            reason=reason,
            final_guard_flags=final_guard_flags,
            session_key=session_key,
            visible_turn_kind=_safe_str(getattr(visible_turn, "turn_kind", "")),
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] uncertainty pause failed: {exc}", flush=True)
        return {"notes": [f"uncertainty_pause_error:{type(exc).__name__}"]}


def _observe_post_reply_self_observation(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    visible_turn: Any,
    final_guard_flags: list[str],
    expression_learning: dict[str, Any],
    recalled_context: Any,
) -> dict[str, Any]:
    try:
        quality_flags = (
            runtime.speech_controller.reply_quality_flags(payload=payload, user_text=text, reply=reply) if reply else []
        )
        notes = [_safe_str(note) for note in expression_learning.get("notes", [])]
        notes.extend(_safe_str(note) for note in quality_flags)
        expression_learning["notes"] = _dedupe(notes)
        return observe_post_reply_self_observation(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            reply=reply,
            visible_turn=visible_turn,
            final_guard_flags=final_guard_flags,
            quality_flags=quality_flags,
            recalled_context=_safe_str(getattr(recalled_context, "prompt_block", "")),
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] post-reply self observation failed: {exc}", flush=True)
        return {"recorded": False, "notes": [f"post_reply_observation_error:{type(exc).__name__}"]}



def _record_learning_closed_loop(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session_key: str,
    visible_turn: Any,
    final_guard_flags: list[str],
    expression_learning: dict[str, Any],
    post_reply_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        quality_flags = (
            runtime.speech_controller.reply_quality_flags(payload=payload, user_text=text, reply=reply) if reply else []
        )
        expression_notes = [_safe_str(note) for note in expression_learning.get("notes", [])]
        if isinstance(post_reply_observation, dict):
            expression_notes.extend(_safe_str(note) for note in post_reply_observation.get("notes", []))
        return record_learning_closed_loop_turn(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            reply=reply,
            session_key=session_key,
            visible_turn_kind=_safe_str(getattr(visible_turn, "turn_kind", "")),
            final_guard_flags=final_guard_flags,
            quality_flags=quality_flags,
            expression_notes=_dedupe(expression_notes),
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] learning closed loop failed: {exc}", flush=True)
        return {"notes": [f"learning_closed_loop_error:{type(exc).__name__}"]}


def _record_owner_voice_sidecars(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
) -> tuple[dict[str, Any], bool]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    if not _as_bool(metadata.get("is_owner_user"), default=False):
        return {"notes": []}, False
    try:
        overlay = record_voice_trial_overlay(runtime.xinyu_dir, payload, user_text=text, reply=reply, source="qq_gateway")
    except Exception as exc:
        print(f"[xinyu_core_bridge] voice trial overlay failed: {exc}", flush=True)
        overlay = {"notes": [f"voice_trial_overlay_error:{type(exc).__name__}"]}
    calibrated = record_voice_correction(runtime.xinyu_dir, user_text=text, reply=reply, source="qq_gateway")
    return overlay, calibrated


def _record_curiosity_prediction(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session_key: str,
) -> dict[str, Any]:
    try:
        return record_reply_prediction(runtime.xinyu_dir, payload, user_text=text, reply=reply, session_key=session_key)
    except Exception as exc:
        print(f"[xinyu_core_bridge] dialogue curiosity prediction failed: {exc}", flush=True)
        return {"notes": [f"dialogue_curiosity_prediction_error:{type(exc).__name__}"]}


def _record_private_thought_link(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session_key: str,
) -> dict[str, Any]:
    try:
        return record_private_thought_reply_link(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            reply=reply,
            session_key=session_key,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] private thought reply link failed: {exc}", flush=True)
        return {"notes": [f"private_thought_link_error:{type(exc).__name__}"]}


def _archive_dialogue_turn(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    visible_turn: Any,
    final_guard_flags: list[str],
) -> dict[str, Any]:
    try:
        return archive_dialogue_turn(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            assistant_reply=reply,
            message_type=_safe_str(getattr(visible_turn, "turn_kind", "")),
            quality_flags=final_guard_flags,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] dialogue archive failed: {exc}", flush=True)
        return {"notes": [f"dialogue_archive_error:{type(exc).__name__}"], "message_ids": []}


def _extract_memory_candidates(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    archive_result: dict[str, Any],
    session: Any,
    visible_turn: Any,
    final_guard_flags: list[str],
    post_reply_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        return extract_memory_candidates(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            assistant_reply=reply,
            source_message_ids=list(archive_result.get("message_ids", [])),
            dialogue_tail=session.dialogue_tail,
            visible_turn=visible_turn,
            quality_flags=final_guard_flags,
            post_reply_observation=post_reply_observation,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] memory candidate extraction failed: {exc}", flush=True)
        return {"notes": [f"memory_candidate_error:{type(exc).__name__}"]}


def _run_memory_self_review(runtime: Any) -> dict[str, Any]:
    try:
        result = run_memory_self_review(runtime.xinyu_dir)
        try:
            maintenance = run_memory_candidate_maintenance(runtime.xinyu_dir)
            result["candidate_maintenance"] = maintenance
            if int(maintenance.get("backfill", {}).get("backfilled") or 0) or int(
                maintenance.get("cleanup", {}).get("archived") or 0
            ):
                result.setdefault("notes", []).append(
                    "memory_candidate_maintenance:"
                    f"{_safe_str(maintenance.get('backfill', {}).get('backfilled'), '0')}/"
                    f"{_safe_str(maintenance.get('cleanup', {}).get('archived'), '0')}"
                )
        except Exception as exc:
            print(f"[xinyu_core_bridge] memory candidate maintenance failed: {exc}", flush=True)
            result.setdefault("notes", []).append(f"memory_candidate_maintenance_error:{type(exc).__name__}")
        if int(result.get("reviewed_candidates") or 0) > 0:
            result.setdefault("notes", []).append(
                "memory_self_review:"
                f"{_safe_str(result.get('reviewed_candidates'), '0')}/"
                f"{_safe_str(result.get('self_approved'), '0')}/"
                f"{_safe_str(result.get('observe_more'), '0')}/"
                f"{_safe_str(result.get('owner_review_required'), '0')}/"
                f"{_safe_str(result.get('blocked'), '0')}"
            )
        return result
    except Exception as exc:
        print(f"[xinyu_core_bridge] memory self-review failed: {exc}", flush=True)
        return {"notes": [f"memory_self_review_error:{type(exc).__name__}"]}


def _record_interaction_journal(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session_key: str,
    visible_turn: Any,
    turn_id: str,
    turn_started_at: float,
) -> dict[str, Any]:
    try:
        result = record_interaction_turn(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            reply=reply,
            session_key=session_key,
            source="qq_gateway",
            turn_kind=_safe_str(getattr(visible_turn, "turn_kind", "")),
            turn_id=turn_id,
            elapsed_ms=int((time.perf_counter() - turn_started_at) * 1000),
        )
        recent_context_guard = ensure_recent_context_health(runtime.xinyu_dir)
        result.setdefault("notes", []).append(
            "recent_context_guard:"
            f"{_safe_str(recent_context_guard.get('status'))}/"
            f"{_safe_str(recent_context_guard.get('action'))}"
        )
        return result
    except Exception as exc:
        print(f"[xinyu_core_bridge] interaction journal failed: {exc}", flush=True)
        return {"notes": [f"interaction_journal_error:{type(exc).__name__}"]}


def _schedule_promised_followup(
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


async def _maybe_enqueue_sticker_reply(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    session_key: str,
    turn_id: str,
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            maybe_enqueue_sticker_reply,
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


def _turn_action_result(
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


def _finish_turn_coherence(
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
) -> dict[str, Any]:
    try:
        return finish_turn_coherence(
            runtime.xinyu_dir,
            turn_id=turn_id,
            payload=payload,
            user_text=text,
            reply=reply,
            action_result=action_result,
            memory_changed=before_memory != _memory_snapshot(runtime.memory_root),
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
