from __future__ import annotations

import sys as _sys
from datetime import datetime
from typing import Any

from xinyu_action_experience_digest import read_recent_action_digest_context
from xinyu_action_feedback_surface import build_action_feedback_prompt_block
from xinyu_bridge_turn_live_state import build_live_turn_state
from xinyu_bridge_turn_prompt_injection import inject_live_turn_context_from_facade
from xinyu_bridge_turn_time_facts import (
    TIME_FACT_CORRECTION_CUES,
    TIME_FACT_CUES,
    looks_like_time_fact_correction as _runtime_looks_like_time_fact_correction,
)
from xinyu_bridge_turn_transport_sidecars import collect_transport_sidecars
from xinyu_bridge_values import as_bool, safe_str
from xinyu_conversation_experience_sidecar import build_conversation_experience_prompt_block
from xinyu_daily_digest import build_daily_digest_prompt_block
from xinyu_dialogue_rule_trial_overlay import build_dialogue_rule_trial_overlay_prompt_block
from xinyu_experience_frame import read_recent_action_context
from xinyu_initiative_spine import build_initiative_spine_prompt_block
from xinyu_intention_ecology import build_intention_ecology_prompt_block
from xinyu_learning_closed_loop import build_learning_closed_loop_prompt_block
from xinyu_memory_braid import build_memory_braid_prompt_block
from xinyu_owner_context_bridge import build_owner_continuity_hint as build_owner_context_hint
from xinyu_prompt_pressure import PromptSidecar, select_prompt_sidecars, write_prompt_pressure_report
from xinyu_recent_attachment_context import load_recent_attachment_context
from xinyu_relation_posture import build_relation_posture_prompt_block
from xinyu_runtime_context import build_goldmark_auth_prompt_block
from xinyu_self_state_capsule import build_self_state_capsule_prompt_block
from xinyu_short_term_continuity import build_short_term_continuity_prompt_block
from xinyu_short_term_recall_diagnostics import build_short_term_recall_diagnostics
from xinyu_short_term_recall_diagnostics import write_short_term_recall_diagnostics
from xinyu_slow_state_modulator import render_slow_state_prompt_block
from xinyu_text_variants import readable_markers
from xinyu_turn_coherence import build_turn_coherence_prompt_block
from xinyu_turn_triage_gate import render_turn_triage_prompt_block
from xinyu_voice_trial_overlay import build_voice_trial_overlay_prompt_block


REPLY_DEMO_REQUEST_MARKERS = readable_markers(
    "你会怎么回",
    "你会怎么回应",
    "你会怎么说",
    "你怎么回",
    "你怎么回应",
    "你怎么接",
    "会怎么回",
    "会怎么回应",
    "会怎么说",
    "会怎么接",
    "叫你一声",
    "喊你一声",
)

ACTION_NARRATION_FORBID_MARKERS = readable_markers(
    "不要演戏动作",
    "别演戏动作",
    "不要动作",
    "别动作",
    "不要演戏",
    "别演戏",
    "不要角色扮演",
    "别角色扮演",
)

SIBLING_REPLY_DEMO_USER_MARKERS = readable_markers("妹妹", "哥哥", "哥", "叫你一声", "喊你一声")


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def looks_like_time_fact_correction(text: str) -> bool:
    return _runtime_looks_like_time_fact_correction(text, safe_str_func=safe_str)


def inject_live_turn_context(
    runtime: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    text: str,
    turn_id: str = "",
    dialogue_tail: list[dict[str, str]] | None = None,
    persona_context: str = "",
    curiosity_context: str = "",
    visible_turn: Any | None = None,
    recalled_context: str = "",
    runtime_presence_context: str = "",
    continuity_context: str = "",
    uncertainty_pause_context: str = "",
    life_reply_context: str = "",
    emotion_council_context: str = "",
    codex_delegate_open: str = "",
    codex_delegate_close: str = "",
) -> None:
    return inject_live_turn_context_from_facade(
        _sys.modules[__name__],
        runtime,
        agent,
        payload=payload,
        text=text,
        turn_id=turn_id,
        dialogue_tail=dialogue_tail,
        persona_context=persona_context,
        curiosity_context=curiosity_context,
        visible_turn=visible_turn,
        recalled_context=recalled_context,
        runtime_presence_context=runtime_presence_context,
        continuity_context=continuity_context,
        uncertainty_pause_context=uncertainty_pause_context,
        life_reply_context=life_reply_context,
        emotion_council_context=emotion_council_context,
        codex_delegate_open=codex_delegate_open,
        codex_delegate_close=codex_delegate_close,
    )

__all__ = (
    "ACTION_NARRATION_FORBID_MARKERS",
    "Any",
    "PromptSidecar",
    "REPLY_DEMO_REQUEST_MARKERS",
    "SIBLING_REPLY_DEMO_USER_MARKERS",
    "TIME_FACT_CORRECTION_CUES",
    "TIME_FACT_CUES",
    "_has_any",
    "_runtime_looks_like_time_fact_correction",
    "_sys",
    "annotations",
    "as_bool",
    "build_action_feedback_prompt_block",
    "build_conversation_experience_prompt_block",
    "build_daily_digest_prompt_block",
    "build_dialogue_rule_trial_overlay_prompt_block",
    "build_goldmark_auth_prompt_block",
    "build_initiative_spine_prompt_block",
    "build_intention_ecology_prompt_block",
    "build_learning_closed_loop_prompt_block",
    "build_live_turn_state",
    "build_memory_braid_prompt_block",
    "build_owner_context_hint",
    "build_relation_posture_prompt_block",
    "build_self_state_capsule_prompt_block",
    "build_short_term_continuity_prompt_block",
    "build_short_term_recall_diagnostics",
    "build_turn_coherence_prompt_block",
    "build_voice_trial_overlay_prompt_block",
    "collect_transport_sidecars",
    "datetime",
    "inject_live_turn_context",
    "inject_live_turn_context_from_facade",
    "load_recent_attachment_context",
    "looks_like_time_fact_correction",
    "read_recent_action_context",
    "read_recent_action_digest_context",
    "readable_markers",
    "render_slow_state_prompt_block",
    "render_turn_triage_prompt_block",
    "safe_str",
    "select_prompt_sidecars",
    "write_prompt_pressure_report",
    "write_short_term_recall_diagnostics",
)
