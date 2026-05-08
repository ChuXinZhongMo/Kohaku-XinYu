from __future__ import annotations

import asyncio
import time
from typing import Any

from xinyu_action_experience_digest import compose_action_digest_followup, digest_action_experience_residue
from xinyu_action_layer import codex_response_to_outcome
from xinyu_action_reply_composer import compose_action_reply
from xinyu_codex_delegate import looks_like_owner_local_write_request
from xinyu_experience_frame import (
    build_experience_frame,
    compose_recent_action_followup,
    write_action_experience_residue,
    write_recent_action_experience,
)
from xinyu_memory_event_sourcing import record_action_experience_event
from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_runtime_presence import record_turn_finished
from xinyu_sent_reply_index import visible_text_hash
from xinyu_tool_protocol import ActionOutcome, DELEGATED_LOCAL_RISK
from xinyu_visible_state_hygiene import sanitize_visible_state_files


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _command_id(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return _safe_str(metadata.get("desktop_command_id") or payload.get("command_id"))


async def settle_action_experience(
    runtime: Any,
    payload: dict[str, Any],
    *,
    request: dict[str, Any],
    outcome: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    notes: list[str] = []
    frame = build_experience_frame(request, outcome)
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
        memory_event = record_action_experience_event(runtime.xinyu_dir, payload, frame=frame, outcome=outcome)
        notes.extend(_safe_str(note) for note in memory_event.get("notes", [])[:4])
    except Exception as exc:
        notes.append(f"action_experience_memory_error:{type(exc).__name__}")
    try:
        residue = write_action_experience_residue(runtime.xinyu_dir, frame, outcome)
        notes.extend(_safe_str(note) for note in residue.get("notes", [])[:2])
        if residue.get("written"):
            digest = digest_action_experience_residue(runtime.xinyu_dir, max_items=3)
            notes.extend(_safe_str(note) for note in digest.get("notes", [])[:3])
    except Exception as exc:
        notes.append(f"action_experience_residue_error:{type(exc).__name__}")
    try:
        recent = write_recent_action_experience(runtime.xinyu_dir, frame, outcome)
        notes.extend(_safe_str(note) for note in recent.get("notes", [])[:2])
    except Exception as exc:
        notes.append(f"recent_action_experience_error:{type(exc).__name__}")
    try:
        hygiene = sanitize_visible_state_files(runtime.xinyu_dir)
        changed_count = int(hygiene.get("changed_count") or 0)
        if changed_count:
            notes.append(f"visible_state_hygiene:{changed_count}")
    except Exception as exc:
        notes.append(f"visible_state_hygiene_error:{type(exc).__name__}")
    return frame, self_choice_public, notes


async def handle_action_layer_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    bridge_request_error_type: type[BaseException] | None = None,
) -> dict[str, Any] | None:
    decision = runtime.action_layer.route(payload, text, turn_id=turn_id)
    if decision.kind != "action_request" or decision.request is None:
        return None

    request = decision.request
    request_dict = request.to_dict()
    if request.tool == "codex_delegate":
        try:
            task_text = _safe_str(request.params.get("task_text")).strip() or text
            codex_payload = runtime._build_model_codex_payload(payload, session_key=session_key, task_text=task_text)
            metadata = codex_payload.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
                codex_payload["metadata"] = metadata
            metadata["delegated_by_action_layer"] = True
            if bool(metadata.get("is_owner_user")) and looks_like_owner_local_write_request(task_text):
                metadata["owner_local_write_approved"] = True
                metadata["owner_local_write_source"] = "owner_private_action_layer"
            metadata["action_layer_request"] = request_dict
            codex_response = await runtime.codex_execute(codex_payload)
            outcome = codex_response_to_outcome(codex_response, request)
        except Exception as exc:
            if bridge_request_error_type is not None and isinstance(exc, bridge_request_error_type):
                status = getattr(exc, "status", None)
                status_value = getattr(status, "value", status)
                outcome = ActionOutcome.failed(
                    tool="codex_delegate",
                    summary=_safe_str(getattr(exc, "message", str(exc))),
                    error_code=f"bridge_request_error:{status_value}",
                    risk=DELEGATED_LOCAL_RISK,
                    notes=["codex_delegate_bridge_rejected"],
                ).to_dict()
            else:
                outcome = ActionOutcome.failed(
                    tool="codex_delegate",
                    summary=f"Codex 委派没有启动：{type(exc).__name__}",
                    error_code=type(exc).__name__,
                    risk=DELEGATED_LOCAL_RISK,
                    notes=["codex_delegate_bridge_exception"],
                ).to_dict()
    else:
        outcome = await asyncio.to_thread(
            runtime.action_layer.execute,
            request,
            payload,
            bridge_snapshot=runtime.health_snapshot(),
        )

    frame, self_choice_public, experience_notes = await settle_action_experience(
        runtime,
        payload,
        request=request_dict,
        outcome=outcome,
    )
    reply = compose_action_reply(outcome, frame=frame, self_choice_public=self_choice_public)
    guarded_reply, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=text,
        reply=reply,
    )
    if guarded_reply:
        reply = guarded_reply

    notes: list[str] = [
        "action_layer_intercepted",
        f"action_layer_tool:{request.tool}",
    ]
    notes.extend(decision.notes[:4])
    notes.extend(_safe_str(note) for note in outcome.get("notes", [])[:5])
    notes.extend(experience_notes[:8])
    notes.extend(_safe_str(note) for note in event_sidecar.get("notes", [])[:3])
    if guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(guard_flags[:3]))
    if cleanup.get("cleaned_sessions"):
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")

    after_memory = _memory_snapshot(runtime.memory_root)
    memory_changed = before_memory != after_memory
    elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=elapsed_ms,
        status="ok" if outcome.get("ok") or outcome.get("result") == "blocked_by_boundary" else "error",
        notes=notes,
        memory_changed=memory_changed,
    )
    reply_hash = visible_text_hash(reply)
    await runtime._desktop_publish_chat_finished(
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        started_at=turn_started_wall,
        elapsed_ms=elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=[],
        reply_hash=reply_hash,
        recall_event_id="",
        recall_count=0,
        top_recall_sources=[],
    )
    return {
        "accepted": True,
        "reply": reply,
        "memory_changed": memory_changed,
        "turn_id": turn_id,
        "command_id": _command_id(payload),
        "session_id": session_key,
        "reply_hash": reply_hash,
        "archive_message_ids": [],
        "archive_assistant_message_id": "",
        "action_outcome": outcome,
        "experience_frame": frame,
        "notes": notes,
    }


async def handle_recent_action_followup_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
) -> dict[str, Any] | None:
    if not runtime._owner_private_payload_matches(payload):
        return None
    followup = compose_recent_action_followup(runtime.xinyu_dir, text)
    if not followup:
        return None

    reply = _safe_str(followup.get("reply")).strip()
    if not reply:
        return None
    guarded_reply, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=text,
        reply=reply,
    )
    if guarded_reply:
        reply = guarded_reply

    row = followup.get("row") if isinstance(followup.get("row"), dict) else {}
    notes: list[str] = ["recent_action_followup_intercepted"]
    notes.extend(_safe_str(note) for note in followup.get("notes", [])[:5])
    if row:
        notes.append(f"recent_action_followup_result:{_safe_str(row.get('result'), 'unknown')}")
    notes.extend(_safe_str(note) for note in event_sidecar.get("notes", [])[:3])
    if guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(guard_flags[:3]))
    if cleanup.get("cleaned_sessions"):
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")

    after_memory = _memory_snapshot(runtime.memory_root)
    memory_changed = before_memory != after_memory
    elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
    )
    reply_hash = visible_text_hash(reply)
    await runtime._desktop_publish_chat_finished(
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        started_at=turn_started_wall,
        elapsed_ms=elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=[],
        reply_hash=reply_hash,
        recall_event_id="",
        recall_count=0,
        top_recall_sources=[],
    )
    return {
        "accepted": True,
        "reply": reply,
        "memory_changed": memory_changed,
        "turn_id": turn_id,
        "command_id": _command_id(payload),
        "session_id": session_key,
        "reply_hash": reply_hash,
        "archive_message_ids": [],
        "archive_assistant_message_id": "",
        "recent_action_followup": {
            "mode": _safe_str(followup.get("mode")),
            "tool": _safe_str(row.get("tool")),
            "target_alias": _safe_str(row.get("target_alias")),
            "result": _safe_str(row.get("result")),
        },
        "notes": notes,
    }


async def handle_action_digest_followup_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any],
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
) -> dict[str, Any] | None:
    if not runtime._owner_private_payload_matches(payload):
        return None
    followup = compose_action_digest_followup(runtime.xinyu_dir, text)
    if not followup:
        return None

    reply = _safe_str(followup.get("reply")).strip()
    if not reply:
        return None
    guarded_reply, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=text,
        reply=reply,
    )
    if guarded_reply:
        reply = guarded_reply

    row = followup.get("row") if isinstance(followup.get("row"), dict) else {}
    notes: list[str] = ["action_digest_followup_intercepted"]
    notes.extend(_safe_str(note) for note in followup.get("notes", [])[:5])
    if row:
        notes.append(f"action_digest_seed:{_safe_str(row.get('seed_id'), 'none')}")
    notes.extend(_safe_str(note) for note in event_sidecar.get("notes", [])[:3])
    if guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(guard_flags[:3]))
    if cleanup.get("cleaned_sessions"):
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")

    after_memory = _memory_snapshot(runtime.memory_root)
    memory_changed = before_memory != after_memory
    elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
    )
    reply_hash = visible_text_hash(reply)
    await runtime._desktop_publish_chat_finished(
        payload,
        text=text,
        reply=reply,
        session_key=session_key,
        turn_id=turn_id,
        started_at=turn_started_wall,
        elapsed_ms=elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
        archive_message_ids=[],
        reply_hash=reply_hash,
        recall_event_id="",
        recall_count=0,
        top_recall_sources=[],
    )
    return {
        "accepted": True,
        "reply": reply,
        "memory_changed": memory_changed,
        "turn_id": turn_id,
        "command_id": _command_id(payload),
        "session_id": session_key,
        "reply_hash": reply_hash,
        "archive_message_ids": [],
        "archive_assistant_message_id": "",
        "action_digest_followup": {
            "mode": _safe_str(followup.get("mode")),
            "seed_id": _safe_str(row.get("seed_id")),
            "reflection_item_id": _safe_str(row.get("reflection_item_id")),
        },
        "notes": notes,
    }
