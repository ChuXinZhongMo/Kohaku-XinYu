from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ReplyPipelineState:
    reply: str
    rendered: bool = False
    renderer_reason: str = ""
    final_guard_flags: list[str] = field(default_factory=list)
    final_guard_applied: bool = False
    expression_learning: dict[str, Any] = field(default_factory=dict)
    visible_dedupe: Any = None
    stale_context_reply_replaced: bool = False
    life_reply_adjustment: dict[str, Any] = field(default_factory=dict)
    current_sticker_reply: Any = ""
    recent_sticker_reply: Any = ""
    reply_bubble_force_units: Any = field(default_factory=list)
    empty_visible_reply_no_fallback: bool = False


def reply_pipeline_result(state: ReplyPipelineState) -> dict[str, Any]:
    return {
        "reply": state.reply,
        "rendered": state.rendered,
        "renderer_reason": state.renderer_reason,
        "final_guard_flags": state.final_guard_flags,
        "final_guard_applied": state.final_guard_applied,
        "expression_learning": state.expression_learning,
        "visible_dedupe": state.visible_dedupe,
        "stale_context_reply_replaced": state.stale_context_reply_replaced,
        "life_reply_adjustment": state.life_reply_adjustment,
        "current_sticker_reply": state.current_sticker_reply,
        "recent_sticker_reply": state.recent_sticker_reply,
        "reply_bubble_force_units": state.reply_bubble_force_units,
        "empty_visible_reply_no_fallback": state.empty_visible_reply_no_fallback,
    }
