from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from xinyu_bridge_state_text import build_payload_time_context_block
from xinyu_bridge_turn_live_state_payload import (
    build_live_turn_payload_state,
    live_turn_pressure_line,
    live_turn_residue_line,
)
from xinyu_intention_ecology import evaluate_intention_ecology
from xinyu_life_posture import build_life_posture
from xinyu_persona_runtime import build_persona_runtime_state
from xinyu_relation_posture import evaluate_relation_posture
from xinyu_scene_frame import build_scene_frame
from xinyu_slow_state_modulator import build_slow_state
from xinyu_turn_classifier import classify_visible_turn
from xinyu_turn_residue import read_turn_residue
from xinyu_turn_triage_gate import triage_turn


@dataclass(frozen=True)
class LiveTurnState:
    metadata: dict[str, Any]
    session_key: str
    is_owner: bool
    source_line: str
    relationship_line: str
    sender_name: str
    time_context_block: str
    visible_turn: Any
    life_posture: Any
    persona_runtime: Any
    previous_residue: Any
    scene_frame: Any
    turn_triage: Any
    slow_state: Any
    relation_posture: Any
    intention_ecology: Any
    pressure_line: str
    residue_line: str
    tail_block: str


def build_live_turn_state(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    dialogue_tail: list[dict[str, str]] | None,
    visible_turn: Any | None,
    recalled_context: str,
    runtime_presence_context: str,
    continuity_context: str,
) -> LiveTurnState:
    payload_state = build_live_turn_payload_state(runtime, payload)
    time_context_block = build_payload_time_context_block(payload)
    if visible_turn is None:
        visible_turn = classify_visible_turn(runtime.xinyu_dir, payload=payload, user_text=text)
    life_posture = build_life_posture(runtime.xinyu_dir, payload=payload, user_text=text, visible_turn=visible_turn)
    persona_runtime = build_persona_runtime_state(
        runtime.xinyu_dir,
        payload=payload,
        user_text=text,
        draft_reply="",
    )
    previous_residue = read_turn_residue(runtime.xinyu_dir)
    scene_frame = build_scene_frame(
        runtime.xinyu_dir,
        user_text=text,
        visible_turn=visible_turn,
        canonical_recall_context=recalled_context,
    )
    turn_triage = triage_turn(
        runtime.xinyu_dir,
        user_text=text,
        payload=payload,
        visible_turn=visible_turn,
        scene_frame=scene_frame,
        recent_work_context=f"{runtime_presence_context}\n{continuity_context}",
        canonical_recall_context=recalled_context,
    )
    slow_state = build_slow_state(
        runtime.xinyu_dir,
        user_text=text,
        scene_frame=scene_frame,
        triage_decision=turn_triage,
        turn_residue=previous_residue,
        persist=True,
    )
    evaluated_at = datetime.now().astimezone().isoformat()
    relation_posture = evaluate_relation_posture(
        runtime.xinyu_dir,
        payload,
        user_text=text,
        dialogue_tail=dialogue_tail or [],
        visible_turn=visible_turn,
        scene_frame=scene_frame,
        turn_triage=turn_triage,
        evaluated_at=evaluated_at,
        write_state=True,
    )
    intention_ecology = evaluate_intention_ecology(
        runtime.xinyu_dir,
        payload,
        user_text=text,
        dialogue_tail=dialogue_tail or [],
        relation_posture=relation_posture,
        visible_turn=visible_turn,
        checked_at=evaluated_at,
        write_state=True,
    )

    tail_block = runtime._format_dialogue_tail(dialogue_tail or [])
    return LiveTurnState(
        metadata=payload_state.metadata,
        session_key=payload_state.session_key,
        is_owner=payload_state.is_owner,
        source_line=payload_state.source_line,
        relationship_line=payload_state.relationship_line,
        sender_name=payload_state.sender_name,
        time_context_block=time_context_block,
        visible_turn=visible_turn,
        life_posture=life_posture,
        persona_runtime=persona_runtime,
        previous_residue=previous_residue,
        scene_frame=scene_frame,
        turn_triage=turn_triage,
        slow_state=slow_state,
        relation_posture=relation_posture,
        intention_ecology=intention_ecology,
        pressure_line=live_turn_pressure_line(visible_turn, is_owner=payload_state.is_owner),
        residue_line=live_turn_residue_line(previous_residue),
        tail_block=tail_block,
    )
