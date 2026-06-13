from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_reply_source import final_text_source_for_renderer, note_for_final_text_source


def build_semantic_fast_notes(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    decision: dict[str, Any],
    event_sidecar: dict[str, Any],
    cleanup: dict[str, Any],
    renderer_name: str,
    elapsed_ms: int,
    intents: tuple[str, ...],
    guard_flags: Any,
    visible_dedupe_notes: Any,
    safe_str_func: Callable[..., str],
    append_post_reply_observation_notes_func: Callable[..., Any],
) -> list[str]:
    notes: list[str] = [
        "owner_private_semantic_fast_intercepted",
        f"semantic_fast_route:{safe_str_func(decision.get('route'), 'fast_path')}",
        f"semantic_fast_elapsed_ms:{elapsed_ms}",
    ]
    if intents:
        notes.append(f"semantic_fast_intents:{','.join(intents)}")
    notes.append(note_for_final_text_source(final_text_source_for_renderer(renderer_name)))
    if renderer_name == "direct":
        notes.append("semantic_fast_direct_reply")
    notes.extend(safe_str_func(note) for note in decision.get("notes", [])[:3])
    notes.extend(safe_str_func(note) for note in event_sidecar.get("notes", [])[:3])
    if guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(guard_flags[:3]))
    notes.extend(safe_str_func(note) for note in visible_dedupe_notes[:3])
    append_post_reply_observation_notes_func(
        runtime,
        payload,
        text=text,
        reply=reply,
        notes=notes,
        guard_flags=guard_flags,
        safe_str_func=safe_str_func,
    )
    if cleanup.get("cleaned_sessions"):
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
    return notes


def append_post_reply_observation_notes(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    reply: str,
    notes: list[str],
    guard_flags: Any,
    safe_str_func: Callable[..., str],
    observe_post_reply_func: Callable[..., dict[str, Any]],
) -> None:
    try:
        quality_flags = runtime.speech_controller.reply_quality_flags(payload=payload, user_text=text, reply=reply)
        post_reply_observation = observe_post_reply_func(
            runtime.xinyu_dir,
            payload,
            user_text=text,
            reply=reply,
            final_guard_flags=guard_flags,
            quality_flags=quality_flags,
            recalled_context="",
        )
        notes.extend(safe_str_func(note) for note in post_reply_observation.get("notes", [])[:3])
    except Exception as exc:
        notes.append(f"post_reply_observation_error:{type(exc).__name__}")


def semantic_fast_memory_changed(
    runtime: Any,
    before_memory: dict[str, Any] | None,
    notes: list[str],
    *,
    memory_snapshot_func: Callable[..., dict[str, Any]],
) -> bool:
    if before_memory is None:
        notes.append("semantic_fast_memory_snapshot_skipped")
        return False
    after_memory = memory_snapshot_func(runtime.memory_root)
    return before_memory != after_memory
