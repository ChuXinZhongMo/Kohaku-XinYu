from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from xinyu_bridge_slow_live_finish_payloads_payload import select_kwargs
from xinyu_bridge_slow_live_finish_payloads_status import runtime_renderer_status


_SUCCESS_NOTE_KEYS = (
    "reply",
    "empty_visible_reply_no_fallback",
    "rendered",
    "renderer_reason",
    "final_guard_flags",
    "final_guard_applied",
    "stale_context_reply_replaced",
    "visible_dedupe",
    "finish_sidecars",
    "proactive_tail_synced",
    "model_codex_delegate_note",
    "wait_to_think_task",
    "curiosity_eval",
    "private_thought_outcome",
    "uncertainty_pause_reply",
    "continuity_handoff",
    "life_reply_policy",
    "life_reply_adjustment",
    "response_error_loop",
    "slow_state_runtime",
    "current_sticker_reply",
    "recent_sticker_reply",
    "reply_bubble_force_units",
    "persona_sidecar",
    "event_sidecar",
    "v1_shadow",
    "tinykernel_shadow",
    "emotion_council",
    "recalled_context_notes",
    "expression_learning",
    "cleanup",
    "session",
)


def build_success_notes_kwargs(source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **select_kwargs(source, _SUCCESS_NOTE_KEYS),
        **runtime_renderer_status(source["runtime"]),
    }


__all__ = ["build_success_notes_kwargs"]
