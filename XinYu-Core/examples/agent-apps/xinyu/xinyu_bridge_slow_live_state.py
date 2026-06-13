from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from xinyu_bridge_state_mapping import DataclassMappingState


@dataclass
class SlowLiveMemoryRecallResult:
    recalled_context: Any = None
    recalled_context_event: dict[str, Any] = field(default_factory=dict)
    recalled_context_notes: list[str] = field(default_factory=list)


@dataclass
class SlowLiveModelContexts:
    continuity_handoff: dict[str, Any]
    runtime_presence_context: str
    life_reply_policy: dict[str, Any]
    emotion_council_context: str


@dataclass(eq=False)
class SlowLiveModelTurnState(DataclassMappingState):
    visible_turn: Any
    recalled_context: Any
    recalled_context_event: dict[str, Any]
    recalled_context_notes: list[str]
    continuity_handoff: dict[str, Any]
    runtime_presence_context: str
    life_reply_policy: dict[str, Any]
    emotion_council_context: str
    persona_sidecar: dict[str, Any]


@dataclass(eq=False)
class SlowLiveEntryState(DataclassMappingState):
    response: dict[str, Any] | None
    session: Any
    proactive_tail_synced: bool
    emotion_council: dict[str, Any]


@dataclass(eq=False)
class SlowLiveResponseState(DataclassMappingState):
    response_error_loop: dict[str, Any]
    slow_state_runtime: dict[str, Any]


@dataclass(eq=False)
class SlowLivePostModelReplyState(DataclassMappingState):
    draft_reply: str
    reply: str
    self_code_task: str
    direct_codex_task: str
    model_codex_task: str
    wait_to_think_task: str
    model_codex_delegate_note: str
    wait_to_think_sidecar: dict[str, Any]
    rendered: bool
    renderer_reason: str
    final_guard_flags: list[str]
    final_guard_applied: bool
    expression_learning: dict[str, Any]
    visible_dedupe: Any
    stale_context_reply_replaced: bool
    life_reply_adjustment: dict[str, Any]
    current_sticker_reply: str
    recent_sticker_reply: str
    reply_bubble_force_units: list[str]
    empty_visible_reply_no_fallback: bool
    response_error_loop: dict[str, Any]
    slow_state_runtime: dict[str, Any]


def coerce_model_turn_state(model_turn: SlowLiveModelTurnState | Mapping[str, Any]) -> SlowLiveModelTurnState:
    if isinstance(model_turn, SlowLiveModelTurnState):
        return model_turn
    return SlowLiveModelTurnState(
        visible_turn=model_turn["visible_turn"],
        recalled_context=model_turn["recalled_context"],
        recalled_context_event=model_turn["recalled_context_event"],
        recalled_context_notes=model_turn["recalled_context_notes"],
        continuity_handoff=model_turn["continuity_handoff"],
        runtime_presence_context=model_turn["runtime_presence_context"],
        life_reply_policy=model_turn["life_reply_policy"],
        emotion_council_context=model_turn["emotion_council_context"],
        persona_sidecar=model_turn["persona_sidecar"],
    )


def coerce_post_model_reply_state(
    post_model_reply: SlowLivePostModelReplyState | Mapping[str, Any],
) -> SlowLivePostModelReplyState:
    if isinstance(post_model_reply, SlowLivePostModelReplyState):
        return post_model_reply
    return SlowLivePostModelReplyState(
        draft_reply=post_model_reply["draft_reply"],
        reply=post_model_reply["reply"],
        self_code_task=post_model_reply["self_code_task"],
        direct_codex_task=post_model_reply["direct_codex_task"],
        model_codex_task=post_model_reply["model_codex_task"],
        wait_to_think_task=post_model_reply["wait_to_think_task"],
        model_codex_delegate_note=post_model_reply["model_codex_delegate_note"],
        wait_to_think_sidecar=post_model_reply["wait_to_think_sidecar"],
        rendered=post_model_reply["rendered"],
        renderer_reason=post_model_reply["renderer_reason"],
        final_guard_flags=post_model_reply["final_guard_flags"],
        final_guard_applied=post_model_reply["final_guard_applied"],
        expression_learning=post_model_reply["expression_learning"],
        visible_dedupe=post_model_reply["visible_dedupe"],
        stale_context_reply_replaced=post_model_reply["stale_context_reply_replaced"],
        life_reply_adjustment=post_model_reply["life_reply_adjustment"],
        current_sticker_reply=post_model_reply["current_sticker_reply"],
        recent_sticker_reply=post_model_reply["recent_sticker_reply"],
        reply_bubble_force_units=post_model_reply["reply_bubble_force_units"],
        empty_visible_reply_no_fallback=post_model_reply["empty_visible_reply_no_fallback"],
        response_error_loop=post_model_reply["response_error_loop"],
        slow_state_runtime=post_model_reply["slow_state_runtime"],
    )
