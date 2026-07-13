from __future__ import annotations

from typing import Any, Callable


async def settle_action_experience(
    runtime: Any,
    payload: dict[str, Any],
    *,
    request: dict[str, Any],
    outcome: dict[str, Any],
    build_experience_frame_func: Callable[..., dict[str, Any]],
    record_action_experience_event_func: Callable[..., dict[str, Any]],
    write_action_experience_residue_func: Callable[..., dict[str, Any]],
    digest_action_experience_residue_func: Callable[..., dict[str, Any]],
    write_recent_action_experience_func: Callable[..., dict[str, Any]],
    sanitize_visible_state_files_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    notes: list[str] = []
    frame = build_experience_frame_func(request, outcome)
    self_choice_public: dict[str, Any] = {}
    try:
        self_choice_public = await runtime.self_choice_store.apply_experience_impulse(frame)
        notes.append("action_experience_self_choice_applied")
    except Exception as exc:
        notes.append(f"action_experience_self_choice_error:{type(exc).__name__}")
        try:
            self_choice_public = await runtime.self_choice_store.snapshot_public(consume_cues=False)
        except Exception:
            self_choice_public = {}
    try:
        memory_event = record_action_experience_event_func(runtime.xinyu_dir, payload, frame=frame, outcome=outcome)
        notes.extend(safe_str_func(note) for note in memory_event.get("notes", [])[:4])
    except Exception as exc:
        notes.append(f"action_experience_memory_error:{type(exc).__name__}")
    try:
        residue = write_action_experience_residue_func(runtime.xinyu_dir, frame, outcome)
        notes.extend(safe_str_func(note) for note in residue.get("notes", [])[:2])
        if residue.get("written"):
            digest = digest_action_experience_residue_func(runtime.xinyu_dir, max_items=3)
            notes.extend(safe_str_func(note) for note in digest.get("notes", [])[:3])
    except Exception as exc:
        notes.append(f"action_experience_residue_error:{type(exc).__name__}")
    try:
        recent = write_recent_action_experience_func(runtime.xinyu_dir, frame, outcome)
        notes.extend(safe_str_func(note) for note in recent.get("notes", [])[:2])
    except Exception as exc:
        notes.append(f"recent_action_experience_error:{type(exc).__name__}")
    try:
        hygiene = sanitize_visible_state_files_func(runtime.xinyu_dir)
        changed_count = int(hygiene.get("changed_count") or 0)
        if changed_count:
            notes.append(f"visible_state_hygiene:{changed_count}")
    except Exception as exc:
        notes.append(f"visible_state_hygiene_error:{type(exc).__name__}")
    return frame, self_choice_public, notes
