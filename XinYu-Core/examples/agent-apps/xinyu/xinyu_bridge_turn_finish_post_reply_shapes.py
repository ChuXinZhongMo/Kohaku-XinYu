from __future__ import annotations

from typing import Any, Callable, Iterable


FINAL_GUARD_BLOCKED_UNSENDABLE_REPLY = "final_guard_blocked_unsendable_reply"


def uncertainty_pause_reason(
    reply: str,
    final_guard_flags: list[str],
    is_waiting_reply_func: Callable[[str], bool],
) -> str:
    if is_waiting_reply_func(reply):
        return "waiting_marker"
    if FINAL_GUARD_BLOCKED_UNSENDABLE_REPLY in final_guard_flags:
        return FINAL_GUARD_BLOCKED_UNSENDABLE_REPLY
    return ""


def visible_turn_kind(visible_turn: Any, safe_str_func: Callable[..., str]) -> str:
    return safe_str_func(getattr(visible_turn, "turn_kind", ""))


def recalled_context_prompt_block(recalled_context: Any, safe_str_func: Callable[..., str]) -> str:
    return safe_str_func(getattr(recalled_context, "prompt_block", ""))


def safe_deduped_notes(
    notes: Iterable[Any],
    *,
    safe_str_func: Callable[..., str],
    dedupe_func: Callable[..., list[Any]],
) -> list[Any]:
    return dedupe_func([safe_str_func(note) for note in notes])


def expression_learning_notes_with_quality(
    expression_learning: dict[str, Any],
    quality_flags: Iterable[Any],
    *,
    safe_str_func: Callable[..., str],
    dedupe_func: Callable[..., list[Any]],
) -> list[Any]:
    return safe_deduped_notes(
        [*expression_learning.get("notes", []), *quality_flags],
        safe_str_func=safe_str_func,
        dedupe_func=dedupe_func,
    )


def learning_closed_loop_expression_notes(
    expression_learning: dict[str, Any],
    post_reply_observation: dict[str, Any] | None,
    *,
    safe_str_func: Callable[..., str],
    dedupe_func: Callable[..., list[Any]],
) -> list[Any]:
    notes = list(expression_learning.get("notes", []))
    if isinstance(post_reply_observation, dict):
        notes.extend(post_reply_observation.get("notes", []))
    return safe_deduped_notes(notes, safe_str_func=safe_str_func, dedupe_func=dedupe_func)


def is_owner_user_payload(payload: dict[str, Any], as_bool_func: Callable[..., bool]) -> bool:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    return as_bool_func(metadata.get("is_owner_user"), default=False)


def error_notes(kind: str, exc: Exception) -> dict[str, list[str]]:
    return {"notes": [f"{kind}:{type(exc).__name__}"]}


def post_reply_observation_error(exc: Exception) -> dict[str, Any]:
    return {"recorded": False, "notes": [f"post_reply_observation_error:{type(exc).__name__}"]}
