from __future__ import annotations

from collections.abc import Callable

from xinyu_bridge_slow_live_notes_normalization import (
    extend_sidecar_notes,
    filtered_sticker_notes,
    notes_from_sidecar,
)
from xinyu_bridge_slow_live_notes_payload import SlowLiveSuccessNotesPayload
from xinyu_bridge_values import safe_str as _safe_str


def build_slow_live_success_notes_from_payload(
    payload: SlowLiveSuccessNotesPayload,
    *,
    notes_from_sidecar_func: Callable[..., list[str]] = notes_from_sidecar,
    safe_str_func: Callable[..., str] = _safe_str,
) -> list[str]:
    notes: list[str] = []
    if not payload.reply:
        notes.append("empty_reply")
    if payload.empty_visible_reply_no_fallback:
        notes.append("empty_visible_reply_no_fallback")
    if payload.rendered:
        notes.append(f"outward_renderer_applied:{payload.renderer_reason or 'unknown'}")
    elif payload.outward_renderer:
        notes.append(f"outward_renderer_skipped:{payload.renderer_mode}")
    if payload.final_guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(payload.final_guard_flags[:3]))
    if payload.final_guard_applied:
        notes.append("final_reply_guard_applied")
    if payload.stale_context_reply_replaced:
        notes.append("stale_context_reply_replaced")
    notes.extend(getattr(payload.visible_dedupe, "notes", []))

    finish_sidecars = payload.finish_sidecars
    if finish_sidecars.get("residue_written"):
        notes.append("persona_surface_residue_updated")
    if finish_sidecars.get("voice_calibrated"):
        notes.append("voice_calibration_recorded")
    voice_trial_overlay = finish_sidecars.get("voice_trial_overlay", {})
    if voice_trial_overlay.get("recorded") or any(
        "error" in safe_str_func(note) for note in voice_trial_overlay.get("notes", [])
    ):
        notes.extend(notes_from_sidecar_func(voice_trial_overlay, 2))
    if payload.persona_sidecar.get("state_changed"):
        notes.append("persona_state_updated")
    if payload.persona_sidecar.get("event_recorded"):
        notes.append("owner_relationship_event_recorded")
    if payload.proactive_tail_synced:
        notes.append("proactive_outbound_tail_synced")
    if finish_sidecars.get("proactive_owner_reply_marked"):
        notes.append("proactive_request_owner_replied")
    if payload.model_codex_delegate_note:
        notes.append(payload.model_codex_delegate_note)
    if payload.wait_to_think_task:
        notes.append("wait_to_think_marker_intercepted")

    extend_sidecar_notes(
        notes,
        (
            (payload.curiosity_eval, 4),
            (finish_sidecars.get("curiosity_prediction", {}), 4),
            (payload.private_thought_outcome, 3),
            (payload.uncertainty_pause_reply, 2),
            (payload.continuity_handoff, 2),
            (payload.life_reply_policy, 3),
            (payload.life_reply_adjustment, 3),
            (payload.response_error_loop, 2),
            (payload.slow_state_runtime, 2),
        ),
        notes_from_sidecar_func=notes_from_sidecar_func,
    )
    if payload.current_sticker_reply:
        notes.append("current_sticker_question_answered")
    if payload.recent_sticker_reply:
        notes.append("recent_sticker_question_answered")
    if payload.reply_bubble_force_units:
        notes.append(f"reply_bubble_force_units:{len(payload.reply_bubble_force_units)}")

    extend_sidecar_notes(
        notes,
        (
            (finish_sidecars.get("private_thought_link", {}), 3),
            (payload.persona_sidecar, 4),
            (payload.event_sidecar, 4),
            (payload.v1_shadow, 4),
            (payload.tinykernel_shadow, 3),
            (payload.emotion_council, 4),
        ),
        notes_from_sidecar_func=notes_from_sidecar_func,
    )
    notes.extend(safe_str_func(note) for note in payload.recalled_context_notes[:4])
    extend_sidecar_notes(
        notes,
        (
            (finish_sidecars.get("archive_result", {}), 3),
            (finish_sidecars.get("candidate_result", {}), 3),
            (finish_sidecars.get("memory_self_review", {}), 3),
            (finish_sidecars.get("interaction_journal", {}), 3),
            (payload.expression_learning, 3),
            (finish_sidecars.get("learning_closed_loop", {}), 3),
            (finish_sidecars.get("uncertainty_pause", {}), 3),
            (finish_sidecars.get("wait_to_think_sidecar", {}), 3),
            (finish_sidecars.get("promised_followup", {}), 3),
            (finish_sidecars.get("turn_coherence", {}), 3),
        ),
        notes_from_sidecar_func=notes_from_sidecar_func,
    )
    if finish_sidecars.get("sticker_tail_recorded"):
        notes.append("sticker_delivery_tail_recorded")
    notes.extend(filtered_sticker_notes(finish_sidecars.get("sticker_reply", {}), safe_str_func=safe_str_func))
    if payload.cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_idle_sessions:{payload.cleanup['cleaned_sessions']}")
    if getattr(payload.session, "dialogue_tail", None):
        notes.append("dialogue_working_memory_active")
    return notes
