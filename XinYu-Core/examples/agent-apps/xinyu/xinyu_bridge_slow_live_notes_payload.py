from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SlowLiveSuccessNotesPayload:
    reply: str
    empty_visible_reply_no_fallback: bool
    rendered: bool
    renderer_reason: str
    outward_renderer: bool
    renderer_mode: str
    final_guard_flags: list[str]
    final_guard_applied: bool
    stale_context_reply_replaced: bool
    visible_dedupe: Any
    finish_sidecars: dict[str, Any]
    proactive_tail_synced: bool
    model_codex_delegate_note: str
    wait_to_think_task: str
    curiosity_eval: dict[str, Any]
    private_thought_outcome: dict[str, Any]
    uncertainty_pause_reply: dict[str, Any]
    continuity_handoff: dict[str, Any]
    life_reply_policy: dict[str, Any]
    life_reply_adjustment: dict[str, Any]
    response_error_loop: dict[str, Any]
    slow_state_runtime: dict[str, Any]
    current_sticker_reply: str
    recent_sticker_reply: str
    reply_bubble_force_units: list[int]
    persona_sidecar: dict[str, Any]
    event_sidecar: dict[str, Any]
    v1_shadow: dict[str, Any]
    tinykernel_shadow: dict[str, Any]
    emotion_council: dict[str, Any]
    recalled_context_notes: list[str]
    expression_learning: dict[str, Any]
    cleanup: dict[str, Any]
    session: Any
