from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_runtime_repair_status_response import runtime_repair_status_result
from xinyu_bridge_runtime_repair_status_route_diagnostics import RuntimeRepairStatusDiagnostics
from xinyu_bridge_runtime_repair_status_route_payload import RuntimeRepairStatusRoutePayload
from xinyu_bridge_runtime_repair_status_route_visibility import RuntimeRepairStatusVisibility


async def complete_runtime_repair_status_turn(
    payload: dict[str, Any],
    *,
    xinyu_dir: Path,
    memory_root: Path,
    publish_chat_finished_func: Callable[..., Any],
    route_payload: RuntimeRepairStatusRoutePayload,
    diagnostics: RuntimeRepairStatusDiagnostics,
    visibility: RuntimeRepairStatusVisibility,
    notes: list[str],
    memory_snapshot_func: Callable[..., dict[str, Any]],
    finish_coherence_func: Callable[..., dict[str, Any]],
    clock_func: Callable[[], float],
    record_finished_func: Callable[..., Any],
    visible_hash_func: Callable[[str], str],
    timestamp_func: Callable[..., str],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    try:
        coherence = finish_coherence_func(
            xinyu_dir,
            turn_id=route_payload.turn_id,
            payload=payload,
            user_text=route_payload.text,
            reply=visibility.reply,
            action_result="runtime_repair_status_answered",
            memory_changed=route_payload.before_memory != memory_snapshot_func(memory_root),
            final_guard_flags=visibility.guard_flags,
            component_notes={"runtime_status": {"notes": notes}},
        )
        notes.extend(safe_str_func(note) for note in coherence.get("notes", [])[:3])
    except Exception as exc:
        notes.append(f"turn_coherence_error:{type(exc).__name__}")

    after_memory = memory_snapshot_func(memory_root)
    memory_changed = route_payload.before_memory != after_memory
    elapsed_ms = int((clock_func() - route_payload.turn_started_at) * 1000)
    record_finished_func(
        xinyu_dir,
        turn_id=route_payload.turn_id,
        reply=visibility.reply,
        elapsed_ms=elapsed_ms,
        status=visibility.status,
        notes=notes,
        memory_changed=memory_changed,
    )
    reply_hash = visible_hash_func(visibility.reply)
    await publish_chat_finished_func(
        payload,
        text=route_payload.text,
        reply=visibility.reply,
        session_key=route_payload.session_key,
        turn_id=route_payload.turn_id,
        started_at=timestamp_func(route_payload.turn_started_wall),
        elapsed_ms=elapsed_ms,
        status=visibility.status,
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=[],
        reply_hash=reply_hash,
        recall_event_id="",
        recall_count=0,
        top_recall_sources=[],
    )
    return runtime_repair_status_result(
        reply=visibility.reply,
        memory_changed=memory_changed,
        turn_id=route_payload.turn_id,
        session_key=route_payload.session_key,
        reply_hash=reply_hash,
        digest_ok=diagnostics.digest_ok,
        gateway_ok=diagnostics.gateway_ok,
        notes=notes,
    )
