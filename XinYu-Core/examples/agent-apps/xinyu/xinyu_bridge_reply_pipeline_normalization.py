from __future__ import annotations

from typing import Any, Callable


NormalizeBridgeReply = Callable[[str], str]
DedupeNotes = Callable[[list[str]], list[str]]
DedupeVisibleReply = Callable[[str], Any]


async def recover_empty_visible_reply_impl(
    runtime: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    canonical_recall_context: str = "",
    normalize_reply_func: NormalizeBridgeReply,
    dedupe_visible_reply_func: DedupeVisibleReply,
    dedupe_notes_func: DedupeNotes,
) -> tuple[str, list[str]]:
    if not runtime._owner_private_payload_matches(payload):
        return "", []
    try:
        rendered = await runtime._render_outward_reply(
            agent,
            payload=payload,
            user_text=user_text,
            draft_reply="",
            canonical_recall_context=canonical_recall_context,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] empty visible reply recovery failed: {type(exc).__name__}: {exc}", flush=True)
        return "", ["empty_visible_reply_retry_error"]

    recovered = normalize_reply_func(rendered)
    if not recovered:
        return "", ["empty_visible_reply_retry_empty"]

    guarded, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=user_text,
        reply=recovered,
    )
    guard_flags = list(guard_flags)
    if not guarded:
        return "", dedupe_notes_func(["empty_visible_reply_retry_blocked"] + guard_flags)

    visible_dedupe = dedupe_visible_reply_func(guarded)
    return visible_dedupe.text, dedupe_notes_func(
        ["empty_visible_reply_regenerated"] + guard_flags + list(visible_dedupe.notes)
    )


def dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
