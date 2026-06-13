from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_slow_live_notes_format import build_slow_live_success_notes_from_payload
from xinyu_bridge_slow_live_notes_normalization import (
    extend_sidecar_notes,
    filtered_sticker_notes,
    notes_from_sidecar,
)
from xinyu_bridge_slow_live_notes_payload import SlowLiveSuccessNotesPayload
from xinyu_bridge_values import safe_str as _safe_str


def _extend_sidecar_notes(
    notes: list[str],
    sidecars: tuple[tuple[dict[str, Any], int], ...],
    *,
    notes_from_sidecar_func: Callable[..., list[str]],
) -> None:
    extend_sidecar_notes(notes, sidecars, notes_from_sidecar_func=notes_from_sidecar_func)


def _filtered_sticker_notes(
    sticker_reply: dict[str, Any],
    *,
    safe_str_func: Callable[..., str],
) -> list[str]:
    return filtered_sticker_notes(sticker_reply, safe_str_func=safe_str_func)


def build_slow_live_success_notes(
    *,
    reply: str,
    empty_visible_reply_no_fallback: bool,
    rendered: bool,
    renderer_reason: str,
    outward_renderer: bool,
    renderer_mode: str,
    final_guard_flags: list[str],
    final_guard_applied: bool,
    stale_context_reply_replaced: bool,
    visible_dedupe: Any,
    finish_sidecars: dict[str, Any],
    proactive_tail_synced: bool,
    model_codex_delegate_note: str,
    wait_to_think_task: str,
    curiosity_eval: dict[str, Any],
    private_thought_outcome: dict[str, Any],
    uncertainty_pause_reply: dict[str, Any],
    continuity_handoff: dict[str, Any],
    life_reply_policy: dict[str, Any],
    life_reply_adjustment: dict[str, Any],
    response_error_loop: dict[str, Any],
    slow_state_runtime: dict[str, Any],
    current_sticker_reply: str,
    recent_sticker_reply: str,
    reply_bubble_force_units: list[int],
    persona_sidecar: dict[str, Any],
    event_sidecar: dict[str, Any],
    v1_shadow: dict[str, Any],
    tinykernel_shadow: dict[str, Any],
    emotion_council: dict[str, Any],
    recalled_context_notes: list[str],
    expression_learning: dict[str, Any],
    cleanup: dict[str, Any],
    session: Any,
    notes_from_sidecar_func: Callable[..., list[str]] = notes_from_sidecar,
    safe_str_func: Callable[..., str] = _safe_str,
) -> list[str]:
    payload = SlowLiveSuccessNotesPayload(
        reply=reply,
        empty_visible_reply_no_fallback=empty_visible_reply_no_fallback,
        rendered=rendered,
        renderer_reason=renderer_reason,
        outward_renderer=outward_renderer,
        renderer_mode=renderer_mode,
        final_guard_flags=final_guard_flags,
        final_guard_applied=final_guard_applied,
        stale_context_reply_replaced=stale_context_reply_replaced,
        visible_dedupe=visible_dedupe,
        finish_sidecars=finish_sidecars,
        proactive_tail_synced=proactive_tail_synced,
        model_codex_delegate_note=model_codex_delegate_note,
        wait_to_think_task=wait_to_think_task,
        curiosity_eval=curiosity_eval,
        private_thought_outcome=private_thought_outcome,
        uncertainty_pause_reply=uncertainty_pause_reply,
        continuity_handoff=continuity_handoff,
        life_reply_policy=life_reply_policy,
        life_reply_adjustment=life_reply_adjustment,
        response_error_loop=response_error_loop,
        slow_state_runtime=slow_state_runtime,
        current_sticker_reply=current_sticker_reply,
        recent_sticker_reply=recent_sticker_reply,
        reply_bubble_force_units=reply_bubble_force_units,
        persona_sidecar=persona_sidecar,
        event_sidecar=event_sidecar,
        v1_shadow=v1_shadow,
        tinykernel_shadow=tinykernel_shadow,
        emotion_council=emotion_council,
        recalled_context_notes=recalled_context_notes,
        expression_learning=expression_learning,
        cleanup=cleanup,
        session=session,
    )
    return build_slow_live_success_notes_from_payload(
        payload,
        notes_from_sidecar_func=notes_from_sidecar_func,
        safe_str_func=safe_str_func,
    )


__all__ = [
    "SlowLiveSuccessNotesPayload",
    "build_slow_live_success_notes",
    "build_slow_live_success_notes_from_payload",
    "notes_from_sidecar",
]
