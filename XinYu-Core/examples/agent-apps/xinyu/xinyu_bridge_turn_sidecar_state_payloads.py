from __future__ import annotations

from typing import Any


STATE_CONTEXT_MAX_CHARS = 2200


def checked_at_iso(deps: Any) -> str:
    return deps.datetime.now().astimezone().isoformat()


def short_term_continuity_payload(
    *,
    payload: dict[str, Any],
    text: str,
    dialogue_tail: list[dict[str, str]],
    session_key: str,
    turn_id: str,
) -> dict[str, Any]:
    return {
        "payload": payload,
        "user_text": text,
        "dialogue_tail": dialogue_tail,
        "session_key": session_key,
        "turn_id": turn_id,
        "write_state": True,
    }


def memory_braid_payload(
    deps: Any,
    *,
    payload: dict[str, Any],
    text: str,
    dialogue_tail: list[dict[str, str]],
    recalled_context: str,
    runtime_presence_context: str,
    continuity_context: str,
    persona_context: str,
    curiosity_context: str,
    emotion_council_context: str,
) -> dict[str, Any]:
    return {
        "payload": payload,
        "user_text": text,
        "dialogue_tail": dialogue_tail,
        "recalled_context": recalled_context,
        "runtime_presence_context": runtime_presence_context,
        "continuity_context": continuity_context,
        "persona_context": persona_context,
        "curiosity_context": curiosity_context,
        "emotion_council_context": emotion_council_context,
        "checked_at": checked_at_iso(deps),
        "write_state": True,
        "max_chars": STATE_CONTEXT_MAX_CHARS,
    }


def turn_coherence_payload(
    deps: Any,
    *,
    payload: dict[str, Any],
    text: str,
    turn_id: str,
    memory_braid_block: str,
    recalled_context: str,
    runtime_presence_context: str,
    continuity_context: str,
    persona_context: str,
    emotion_council_context: str,
    recent_action_block: str,
    action_digest_block: str,
) -> dict[str, Any]:
    return {
        "payload": payload,
        "user_text": text,
        "turn_id": turn_id,
        "memory_braid_block": memory_braid_block,
        "recalled_context": recalled_context,
        "runtime_presence_context": runtime_presence_context,
        "continuity_context": continuity_context,
        "persona_context": persona_context,
        "emotion_council_context": emotion_council_context,
        "recent_action_context": recent_action_block,
        "action_digest_context": action_digest_block,
        "checked_at": checked_at_iso(deps),
        "write_state": True,
        "max_chars": STATE_CONTEXT_MAX_CHARS,
    }


def self_state_capsule_payload(
    *,
    text: str,
    visible_turn: Any,
    recalled_context: str,
    runtime_presence_context: str,
    persona_context: str,
    emotion_council_context: str,
) -> dict[str, Any]:
    return {
        "user_text": text,
        "visible_turn": visible_turn,
        "recalled_context": recalled_context,
        "runtime_presence_context": runtime_presence_context,
        "persona_context": persona_context,
        "emotion_council_context": emotion_council_context,
        "write_state": True,
    }
