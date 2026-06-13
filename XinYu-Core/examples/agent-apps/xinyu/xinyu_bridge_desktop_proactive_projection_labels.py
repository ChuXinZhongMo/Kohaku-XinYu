from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def proactive_candidate_id(
    request_id: str,
    question: str,
    *,
    desktop_hash: Callable[..., str],
) -> str:
    if request_id not in {"", "none", "unknown"}:
        return request_id
    return desktop_hash(question)


def proactive_state_labels(
    state: str,
    *,
    state_field: Callable[..., str],
    desktop_hash: Callable[..., str],
    desktop_text_preview: Callable[..., str],
    compose_visible_message: Callable[..., str],
    recent_owner_private_turns_func: Callable[..., list[Any]],
) -> dict[str, Any]:
    question = state_field(state, "concrete_question", "")
    focus_label = state_field(state, "focus_label", "")
    evidence_label = state_field(state, "evidence_label", "")
    why_now = state_field(state, "why_now", "")
    after_owner_replies = state_field(state, "after_owner_replies", "")
    return {
        "focusLabel": desktop_text_preview(focus_label, limit=120),
        "dedupeHash": desktop_hash(state_field(state, "dedupe_key", "")),
        "candidatePreview": desktop_text_preview(
            compose_visible_message(
                question,
                source="desktop_proactive_state",
                recent_context=[
                    *recent_owner_private_turns_func(limit=4),
                    focus_label,
                    evidence_label,
                    why_now,
                    after_owner_replies,
                ],
            ),
            limit=240,
        ),
        "whyNowPreview": desktop_text_preview(why_now, limit=220),
    }


def desktop_current_proactive_question(
    root: Path,
    item: dict[str, Any],
    *,
    read_text_safe: Callable[..., str],
    state_field: Callable[..., str],
    safe_str: Callable[..., str],
    item_from_state_func: Callable[..., dict[str, Any]] | None = None,
) -> str:
    state = read_text_safe(root / "memory/context/proactive_request_state.md")
    if not state:
        return ""
    question = safe_str(state_field(state, "concrete_question", "")).strip()
    if not question:
        return ""

    candidate_id = safe_str(item.get("candidateId")).strip()
    request_id = safe_str(item.get("requestId")).strip()
    state_request_id = safe_str(state_field(state, "request_id", "")).strip()
    if state_request_id and state_request_id not in {"none", "unknown"}:
        return question if state_request_id in {candidate_id, request_id} else ""

    if item_from_state_func is not None:
        try:
            current = item_from_state_func(include_final=True)
        except Exception:
            current = {}
        if safe_str(current.get("candidateId")).strip() == candidate_id:
            return question
    return ""
