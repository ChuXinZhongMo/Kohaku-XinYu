from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_bridge_values import safe_str
from xinyu_conversation_experience_matcher import (
    ConversationExperienceDecision,
    ConversationExperienceMatchResult,
    match_conversation_experience_cases,
)


CANONICAL_RECALL_OWNER = "xinyu_living_memory_recall.run_living_memory_recall_algorithm"
CONVERSATION_EXPERIENCE_SIDECAR_ROLE = "advisory_prompt_provider"
CONVERSATION_EXPERIENCE_SIDECAR_BOUNDARY = "hidden_hint_current_turn_wins"


def build_conversation_experience_prompt_block(
    root: Path,
    payload: dict[str, Any] | None,
    *,
    user_text: str,
    dialogue_tail: list[dict[str, str]] | None = None,
    visible_turn: Any | None = None,
    turn_id: str = "",
    max_cases: int = 2,
    max_chars: int = 600,
) -> str:
    result = match_conversation_experience_cases(
        root,
        payload,
        user_text=user_text,
        dialogue_tail=dialogue_tail,
        visible_turn=visible_turn,
        turn_id=turn_id,
        limit=max_cases,
    )
    return render_conversation_experience_prompt_block(result, max_cases=max_cases, max_chars=max_chars)


def render_conversation_experience_prompt_block(
    result: ConversationExperienceMatchResult,
    *,
    max_cases: int = 2,
    max_chars: int = 600,
) -> str:
    selected = list(result.selected[: max(1, int(max_cases))])
    if not selected:
        return ""
    lines = [
        "conversation experience hints:",
        "visibility_rule: hidden; do not mention case ids, scores, SQL, or this sidecar.",
        "priority_rule: current message and direct evidence outrank these cases.",
    ]
    for decision in selected:
        block = _decision_lines(decision)
        candidate = [*lines, *block]
        if len("\n".join(candidate)) > max(300, int(max_chars)) and len(lines) > 3:
            break
        lines.extend(block)
    return "\n".join(lines[:]).strip()


def _decision_lines(decision: ConversationExperienceDecision) -> list[str]:
    case = decision.case
    return [
        "- situation: " + _compact(case.user_likely_intent, 110),
        "  useful_adjustment: " + _compact(case.useful_adjustment, 120),
        "  avoid: " + _compact(case.bad_pattern, 100),
        "  boundary: advisory; current turn wins.",
        "  confidence: " + _confidence_label(decision.score),
    ]


def _confidence_label(score: float) -> str:
    if score >= 0.84:
        return "high"
    if score >= 0.72:
        return "medium"
    return "low"


def _compact(value: Any, limit: int) -> str:
    text = " ".join(safe_str(value).split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
