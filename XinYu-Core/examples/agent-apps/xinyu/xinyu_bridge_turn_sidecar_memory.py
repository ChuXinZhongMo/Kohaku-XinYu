from __future__ import annotations

from typing import Any, NamedTuple

from xinyu_bridge_turn_sidecar_state_payloads import memory_braid_payload, turn_coherence_payload


class MemoryCoherenceBlocks(NamedTuple):
    recent_action: str
    action_digest: str
    action_feedback: str
    memory_braid: str


def collect_memory_coherence_sidecars(
    deps: Any,
    add_sidecar: Any,
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    turn_id: str,
    dialogue_tail: list[dict[str, str]],
    recalled_context: str,
    runtime_presence_context: str,
    continuity_context: str,
    persona_context: str,
    curiosity_context: str,
    emotion_council_context: str,
) -> MemoryCoherenceBlocks:
    recent_action_block = deps.read_recent_action_context(runtime.xinyu_dir)
    action_digest_block = deps.read_recent_action_digest_context(runtime.xinyu_dir)
    action_feedback_block = deps.build_action_feedback_prompt_block(runtime.xinyu_dir)
    memory_braid_block = deps.build_memory_braid_prompt_block(
        runtime.xinyu_dir,
        **memory_braid_payload(
            deps,
            payload=payload,
            text=text,
            dialogue_tail=dialogue_tail,
            recalled_context=recalled_context,
            runtime_presence_context=runtime_presence_context,
            continuity_context=continuity_context,
            persona_context=persona_context,
            curiosity_context=curiosity_context,
            emotion_council_context=emotion_council_context,
        ),
    )
    if memory_braid_block:
        add_sidecar("memory_braid", memory_braid_block, required=True, admission="core")

    turn_coherence_block = deps.build_turn_coherence_prompt_block(
        runtime.xinyu_dir,
        **turn_coherence_payload(
            deps,
            payload=payload,
            text=text,
            turn_id=turn_id,
            memory_braid_block=memory_braid_block,
            recalled_context=recalled_context,
            runtime_presence_context=runtime_presence_context,
            continuity_context=continuity_context,
            persona_context=persona_context,
            emotion_council_context=emotion_council_context,
            recent_action_block=recent_action_block,
            action_digest_block=action_digest_block,
        ),
    )
    if turn_coherence_block:
        add_sidecar("turn_coherence", turn_coherence_block, required=True, admission="core")

    return MemoryCoherenceBlocks(
        recent_action=recent_action_block,
        action_digest=action_digest_block,
        action_feedback=action_feedback_block,
        memory_braid=memory_braid_block,
    )
