from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_memory_event_sourcing import record_chat_event
from xinyu_runtime_presence import record_turn_finished
from xinyu_runtime_security import source_file_digest
from xinyu_sent_reply_index import visible_text_hash
from xinyu_tinykernel_shadow import record_tinykernel_shadow, shadow_enabled
from xinyu_turn_coherence import finish_turn_coherence


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _timestamp_or_now_iso(value: Any) -> str:
    text = _safe_str(value).strip()
    if text:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone().isoformat()
        except ValueError:
            pass
    return datetime.now().astimezone().isoformat()


@dataclass
class PreModelRouteResult:
    response: dict[str, Any] | None
    event_sidecar: dict[str, Any]
    v1_shadow: dict[str, Any]
    tinykernel_shadow: dict[str, Any] = field(default_factory=dict)


async def run_pre_model_routes(
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
) -> PreModelRouteResult:
    event_sidecar: dict[str, Any] = {"notes": ["event_sourcing_not_run"]}
    v1_shadow: dict[str, Any] = {"notes": []}
    try:
        event_sidecar = record_chat_event(runtime.xinyu_dir, payload, text=text)
    except Exception as exc:
        print(f"[xinyu_core_bridge] event sourcing sidecar failed: {exc}", flush=True)
        event_sidecar = {"notes": [f"event_sourcing_error:{type(exc).__name__}"]}

    runtime_status_response = await _maybe_handle_runtime_repair_status_turn(
        runtime,
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )
    if runtime_status_response is not None:
        return PreModelRouteResult(runtime_status_response, event_sidecar, v1_shadow)

    action_layer_response = await runtime._maybe_handle_action_layer_turn(
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )
    if action_layer_response is not None:
        return PreModelRouteResult(action_layer_response, event_sidecar, v1_shadow)

    recent_action_followup = await runtime._maybe_handle_recent_action_followup_turn(
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )
    if recent_action_followup is not None:
        return PreModelRouteResult(recent_action_followup, event_sidecar, v1_shadow)

    action_digest_followup = await runtime._maybe_handle_action_digest_followup_turn(
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )
    if action_digest_followup is not None:
        return PreModelRouteResult(action_digest_followup, event_sidecar, v1_shadow)

    v1_canary_response = await runtime._maybe_handle_v1_canary_turn(
        payload,
        text=text,
        session_key=session_key,
        turn_id=turn_id,
        turn_started_wall=turn_started_wall,
        turn_started_at=turn_started_at,
        before_memory=before_memory,
        cleanup=cleanup,
        event_sidecar=event_sidecar,
    )
    if v1_canary_response is not None:
        return PreModelRouteResult(v1_canary_response, event_sidecar, v1_shadow)

    v1_shadow = await runtime._run_v1_shadow(payload, text=text)
    tinykernel_shadow = await _run_tinykernel_shadow(runtime, payload, text=text, turn_id=turn_id, observed_at=turn_started_wall)
    return PreModelRouteResult(None, event_sidecar, v1_shadow, tinykernel_shadow)


async def _run_tinykernel_shadow(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    turn_id: str,
    observed_at: str,
) -> dict[str, Any]:
    if not shadow_enabled():
        return {"notes": []}

    owner_private = getattr(runtime, "_owner_private_payload_matches", None)
    if callable(owner_private):
        try:
            if not owner_private(payload):
                return {"notes": []}
        except Exception as exc:
            return {"notes": [f"tinykernel_shadow_scope_error:{type(exc).__name__}"]}

    source = _safe_str(payload.get("source") or payload.get("message_type") or "xinyu_bridge", "xinyu_bridge")
    try:
        return await asyncio.to_thread(
            record_tinykernel_shadow,
            Path(runtime.xinyu_dir),
            turn_id=turn_id,
            source=source,
            user_text=text,
            context={
                "recent_turns": [],
                "persona_state": "",
                "owner_profile": "",
                "runtime_state": "",
                "memory_recall": [],
            },
            capabilities={
                "codex_available": True,
                "external_api_available": True,
                "local_tools_available": True,
            },
            observed_at=_timestamp_or_now_iso(observed_at),
        )
    except Exception as exc:
        return {"recorded": False, "ok": False, "notes": [f"tinykernel_shadow_error:{type(exc).__name__}"]}


async def _maybe_handle_runtime_repair_status_turn(
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
    if not _looks_like_runtime_repair_status_question(text):
        return None

    health = runtime.health_snapshot()
    source_digest = source_file_digest(Path(runtime.xinyu_dir) / "xinyu_core_bridge.py")
    running_digest = _safe_str(health.get("source_digest"), "unknown")
    digest_ok = bool(running_digest and running_digest == source_digest)
    gateway_ok = _tcp_connect("127.0.0.1", 6199)
    core_ok = bool(health.get("ok")) and digest_ok
    if core_ok and gateway_ok:
        reply = "刚才那句“还没”是旧进程在回。现在 core 已重启，gateway 也连着，新代码已经加载；下一轮会走新的记忆、思维、动作一致性链路。"
        status = "ok"
    elif core_ok:
        reply = "core 已经是新代码了，但 QQ gateway 这边我没确认到监听状态。先别信“还没”那种旧尾巴，我还得看 gateway。"
        status = "warn"
    else:
        reply = "还没完全好。当前 core 没对上新源码状态，我不能装作修完。"
        status = "warn"

    guarded_reply, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=text,
        reply=reply,
    )
    if guarded_reply:
        reply = guarded_reply

    notes: list[str] = [
        "runtime_repair_status_intercepted",
        f"core_digest:{'ok' if digest_ok else 'mismatch'}",
        f"qq_gateway:{'listening' if gateway_ok else 'not_listening'}",
    ]
    notes.extend(_safe_str(note) for note in event_sidecar.get("notes", [])[:3])
    if guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(guard_flags[:3]))
    if cleanup.get("cleaned_sessions"):
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")

    try:
        coherence = finish_turn_coherence(
            runtime.xinyu_dir,
            turn_id=turn_id,
            payload=payload,
            user_text=text,
            reply=reply,
            action_result="runtime_repair_status_answered",
            memory_changed=before_memory != _memory_snapshot(runtime.memory_root),
            final_guard_flags=guard_flags,
            component_notes={"runtime_status": {"notes": notes}},
        )
        notes.extend(_safe_str(note) for note in coherence.get("notes", [])[:3])
    except Exception as exc:
        notes.append(f"turn_coherence_error:{type(exc).__name__}")

    after_memory = _memory_snapshot(runtime.memory_root)
    memory_changed = before_memory != after_memory
    elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=elapsed_ms,
        status=status,
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
        started_at=_timestamp_or_now_iso(turn_started_wall),
        elapsed_ms=elapsed_ms,
        status=status,
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
        "session_id": session_key,
        "reply_hash": reply_hash,
        "archive_message_ids": [],
        "archive_assistant_message_id": "",
        "runtime_repair_status": {
            "core_digest": "ok" if digest_ok else "mismatch",
            "qq_gateway": "listening" if gateway_ok else "not_listening",
        },
        "notes": notes,
    }


def _looks_like_runtime_repair_status_question(text: str) -> bool:
    compact = re.sub(r"\s+", "", text or "").lower()
    if not compact:
        return False
    if any(marker in compact for marker in ("还没修", "修好了吗", "修好了么", "修完了吗", "修完了么")):
        return True
    if any(marker in compact for marker in ("现在好了吗", "现在好了么", "现在好了嗎", "现在好了没")):
        return True
    return bool(
        any(marker in compact for marker in ("现在", "这次", "刚才"))
        and any(marker in compact for marker in ("好了", "好了吗", "好了么", "修好", "解决"))
        and any(marker in compact for marker in ("系统", "状态", "记忆", "思维", "动作", "回复", "qq", "bridge", "gateway", "core"))
    )


def _tcp_connect(host: str, port: int, timeout: float = 0.5) -> bool:
    import socket

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
