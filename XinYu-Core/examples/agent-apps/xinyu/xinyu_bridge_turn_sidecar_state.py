from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xinyu_bridge_turn_sidecar_state_normalize import normalize_state_sidecar_state
from xinyu_bridge_turn_sidecar_memory import collect_memory_coherence_sidecars
from xinyu_bridge_turn_sidecar_state_payloads import (
    self_state_capsule_payload,
    short_term_continuity_payload,
)


@dataclass(frozen=True)
class TurnSidecarBlocks:
    short_term_continuity: str
    recent_action: str
    action_digest: str
    action_feedback: str
    memory_braid: str


def sidecar_adder(deps: Any, sidecar_candidates: list[Any]) -> Any:
    def add_sidecar(
        name: str,
        *parts: str,
        required: bool = False,
        admission: str = "support",
    ) -> None:
        candidate = deps.PromptSidecar.from_parts(
            name,
            parts,
            required=required,
            admission=admission,
        )
        if candidate.parts:
            sidecar_candidates.append(candidate)

    return add_sidecar


def collect_state_sidecars(
    deps: Any,
    add_sidecar: Any,
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    turn_id: str,
    dialogue_tail: list[dict[str, str]],
    live_state: Any,
    recalled_context: str,
    runtime_presence_context: str,
    continuity_context: str,
    persona_context: str,
    curiosity_context: str,
    emotion_council_context: str,
) -> TurnSidecarBlocks:
    state = normalize_state_sidecar_state(live_state)
    current_visible_turn = state.visible_turn

    turn_triage_block = deps.render_turn_triage_prompt_block(live_state.turn_triage)
    if turn_triage_block:
        add_sidecar("turn_triage_gate", turn_triage_block, required=True, admission="current_turn")

    slow_state_block = (
        deps.render_slow_state_prompt_block(state.slow_state)
        if state.slow_state_active
        else ""
    )
    if slow_state_block:
        add_sidecar("slow_state_modulator", slow_state_block, admission="support")

    relation_posture_block = deps.build_relation_posture_prompt_block(runtime.xinyu_dir, live_state.relation_posture)
    if relation_posture_block:
        add_sidecar("relation_posture", relation_posture_block, required=True, admission="current_turn")

    intention_ecology_block = deps.build_intention_ecology_prompt_block(runtime.xinyu_dir, live_state.intention_ecology)
    if intention_ecology_block:
        add_sidecar("intention_ecology", intention_ecology_block, required=True, admission="current_turn")

    short_term_continuity_block = deps.build_short_term_continuity_prompt_block(
        runtime.xinyu_dir,
        **short_term_continuity_payload(
            payload=payload,
            text=text,
            dialogue_tail=dialogue_tail,
            session_key=live_state.session_key,
            turn_id=turn_id,
        ),
    )
    if short_term_continuity_block:
        add_sidecar(
            "short_term_continuity",
            short_term_continuity_block,
            required=True,
            admission="current_turn",
        )

    memory_coherence = collect_memory_coherence_sidecars(
        deps,
        add_sidecar,
        runtime,
        payload=payload,
        text=text,
        turn_id=turn_id,
        dialogue_tail=dialogue_tail,
        recalled_context=recalled_context,
        runtime_presence_context=runtime_presence_context,
        continuity_context=continuity_context,
        persona_context=persona_context,
        curiosity_context=curiosity_context,
        emotion_council_context=emotion_council_context,
    )

    self_state_capsule_block = deps.build_self_state_capsule_prompt_block(
        runtime.xinyu_dir,
        payload,
        **self_state_capsule_payload(
            text=text,
            visible_turn=current_visible_turn,
            recalled_context=recalled_context,
            runtime_presence_context=runtime_presence_context,
            persona_context=persona_context,
            emotion_council_context=emotion_council_context,
        ),
    )
    if self_state_capsule_block:
        add_sidecar(
            "self_state_capsule",
            self_state_capsule_block,
            required=True,
            admission="current_turn",
        )

    initiative_spine_block = deps.build_initiative_spine_prompt_block(
        runtime.xinyu_dir,
        trigger="live_turn_prompt",
        max_chars=1800,
    )
    if initiative_spine_block:
        add_sidecar("initiative_spine", initiative_spine_block, admission="background")

    return TurnSidecarBlocks(
        short_term_continuity=short_term_continuity_block,
        recent_action=memory_coherence.recent_action,
        action_digest=memory_coherence.action_digest,
        action_feedback=memory_coherence.action_feedback,
        memory_braid=memory_coherence.memory_braid,
    )
