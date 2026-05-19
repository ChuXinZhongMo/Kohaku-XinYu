from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any

import v1_canary_gate
from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_runtime_presence import record_turn_finished
from xinyu_sent_reply_index import visible_text_hash
from xinyu_v1_canary_readiness import record_v1_shadow_observation


V1_OWNER_SIMPLE_CANARY_ENV = "XINYU_V1_OWNER_SIMPLE_CANARY"
V1_CANARY_GREETING_TEXTS = frozenset({"hi", "hello", "hey", "早", "早安", "晚上好", "你好", "在吗"})
V1_CANARY_ACK_TEXTS = frozenset({"嗯", "嗯嗯", "哦", "好", "好的", "好哦", "行", "知道了", "ok"})


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _timestamp_or_now_iso(value: Any = None) -> str:
    text = _safe_str(value).strip()
    if not text:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def _command_id(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return _safe_str(metadata.get("desktop_command_id") or payload.get("command_id"))


def health(runtime: Any) -> dict[str, Any]:
    return {
        "enabled": runtime.v1_enabled,
        "shadow_mode": runtime.v1_shadow_mode,
        "shadow_timeout_seconds": runtime.v1_shadow_timeout_seconds,
        "owner_simple_canary": runtime.v1_owner_simple_canary,
        "canary_timeout_seconds": runtime.v1_canary_timeout_seconds,
        "owner_user_ids_configured": len(runtime.v1_owner_user_ids),
        "loaded": runtime._v1_app is not None,
        "last_trace_id": runtime._v1_last_trace_id,
        "last_route": runtime._v1_last_route,
        "last_error": runtime._v1_last_error,
    }


def ensure_app(runtime: Any) -> Any:
    if runtime._v1_app is not None:
        return runtime._v1_app
    from xinyu_v1.app import XinYuV1App
    from xinyu_v1.config import XinYuV1Config

    runtime._v1_app = XinYuV1App(XinYuV1Config.load(runtime.xinyu_dir))
    return runtime._v1_app


def record_shadow_readiness(
    runtime: Any,
    shadow_payload: dict[str, Any],
    *,
    accepted: bool,
    route: str,
    trace_id: str,
    elapsed_ms: int,
    error: str = "",
) -> list[str]:
    try:
        readiness = record_v1_shadow_observation(
            runtime.xinyu_dir,
            accepted=accepted,
            route=route,
            trace_id=trace_id,
            elapsed_ms=elapsed_ms,
            error=error,
            payload=shadow_payload,
        )
    except Exception as exc:
        return [f"v1_canary_readiness_error:{type(exc).__name__}"]
    notes = readiness.get("notes") if isinstance(readiness, dict) else []
    if not isinstance(notes, list):
        return []
    return [_safe_str(note) for note in notes[:4]]


async def run_shadow(runtime: Any, payload: dict[str, Any], *, text: str) -> dict[str, Any]:
    if not runtime.v1_shadow_mode:
        return {"notes": []}
    started = time.monotonic()
    shadow_payload: dict[str, Any] = {}
    try:
        app = ensure_app(runtime)
        shadow_payload = dict(payload)
        shadow_payload.setdefault("text", text)
        metadata = shadow_payload.get("metadata")
        shadow_payload["metadata"] = dict(metadata) if isinstance(metadata, dict) else {}
        shadow_payload["metadata"]["v1_shadow_source"] = "xinyu_core_bridge"
        user_id = _safe_str(shadow_payload.get("user_id")).strip()
        if user_id and user_id in runtime.v1_owner_user_ids:
            shadow_payload["metadata"]["is_owner_user"] = True
        reply = await asyncio.wait_for(
            app.shadow_payload(shadow_payload),
            timeout=runtime.v1_shadow_timeout_seconds,
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        runtime._v1_last_error = ""
        runtime._v1_last_trace_id = reply.trace_id
        runtime._v1_last_route = reply.route
        readiness_notes = record_shadow_readiness(
            runtime,
            shadow_payload,
            accepted=reply.accepted,
            route=reply.route,
            trace_id=reply.trace_id,
            elapsed_ms=elapsed_ms,
        )
        return {
            "accepted": reply.accepted,
            "route": reply.route,
            "trace_id": reply.trace_id,
            "elapsed_ms": elapsed_ms,
            "notes": [
                f"v1_shadow_route:{reply.route or 'unknown'}",
                f"v1_shadow_elapsed_ms:{elapsed_ms}",
                *readiness_notes,
            ],
        }
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        runtime._v1_last_error = f"{type(exc).__name__}: {exc}"
        print(f"[xinyu_core_bridge] v1 shadow failed: {runtime._v1_last_error}", flush=True)
        readiness_notes = record_shadow_readiness(
            runtime,
            shadow_payload if shadow_payload else dict(payload),
            accepted=False,
            route="",
            trace_id="",
            elapsed_ms=elapsed_ms,
            error=f"{type(exc).__name__}: {exc}",
        )
        return {
            "accepted": False,
            "route": "",
            "trace_id": "",
            "elapsed_ms": elapsed_ms,
            "notes": [f"v1_shadow_error:{type(exc).__name__}", *readiness_notes],
        }


def canary_payload_allowed(runtime: Any, payload: dict[str, Any], text: str) -> tuple[bool, list[str]]:
    return v1_canary_gate.canary_payload_allowed(
        v1_enabled=runtime.v1_enabled,
        owner_simple_canary=runtime.v1_owner_simple_canary,
        owner_private=runtime._owner_private_payload_matches(payload),
        payload=payload,
        text=text,
        owner_simple_canary_env=V1_OWNER_SIMPLE_CANARY_ENV,
        greeting_texts=V1_CANARY_GREETING_TEXTS,
        ack_texts=V1_CANARY_ACK_TEXTS,
    )


async def handle_canary_turn(
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
    allowed, canary_reasons = canary_payload_allowed(runtime, payload, text)
    if not allowed:
        return None

    started = time.perf_counter()
    try:
        app = ensure_app(runtime)
        v1_payload = dict(payload)
        metadata = v1_payload.get("metadata")
        v1_payload["metadata"] = dict(metadata) if isinstance(metadata, dict) else {}
        v1_payload["metadata"]["is_owner_user"] = True
        v1_payload["metadata"]["v1_canary_source"] = "xinyu_core_bridge"
        turn = app.normalizer.normalize(v1_payload)
        decision = app.router.decide(turn)
        if getattr(decision.route, "value", "") != "fast_path":
            return None
        v1_reply = await asyncio.wait_for(app.handle_turn(turn), timeout=runtime.v1_canary_timeout_seconds)
    except Exception as exc:
        runtime._v1_last_error = f"{type(exc).__name__}: {exc}"
        print(f"[xinyu_core_bridge] v1 canary failed: {runtime._v1_last_error}", flush=True)
        return None

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    route = _safe_str(getattr(v1_reply, "route", ""))
    trace_id = _safe_str(getattr(v1_reply, "trace_id", ""))
    reply = _safe_str(getattr(v1_reply, "reply", "")).strip()
    runtime._v1_last_error = ""
    runtime._v1_last_trace_id = trace_id
    runtime._v1_last_route = route
    if route != "fast_path" or not getattr(v1_reply, "accepted", False) or not reply:
        return None

    guarded_reply, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=text,
        reply=reply,
    )
    if guarded_reply:
        reply = guarded_reply

    notes: list[str] = [
        "v1_canary_intercepted",
        f"v1_canary_route:{route}",
        f"v1_canary_elapsed_ms:{elapsed_ms}",
    ]
    notes.extend(canary_reasons[:3])
    notes.extend(_safe_str(note) for note in getattr(v1_reply, "notes", ())[:5])
    notes.extend(_safe_str(note) for note in event_sidecar.get("notes", [])[:3])
    if guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(guard_flags[:3]))
    if cleanup.get("cleaned_sessions"):
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")

    after_memory = _memory_snapshot(runtime.memory_root)
    memory_changed = before_memory != after_memory or bool(getattr(v1_reply, "memory_changed", False))
    total_elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=total_elapsed_ms,
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
        started_at=_timestamp_or_now_iso(turn_started_wall),
        elapsed_ms=total_elapsed_ms,
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
        "v1_canary": {
            "scope": "owner_private_simple_messages_only",
            "route": route,
            "trace_id": trace_id,
            "elapsed_ms": elapsed_ms,
            "fallback_available": True,
        },
        "notes": notes,
    }
