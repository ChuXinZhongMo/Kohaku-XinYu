from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import v1_canary_gate
from xinyu_bridge_memory_snapshot import memory_snapshot as _memory_snapshot
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_runtime_presence import record_turn_finished
from xinyu_sent_reply_index import visible_text_hash
from xinyu_turn_route_trace import record_turn_route_stage
from xinyu_visible_reply_guard import dedupe_visible_reply


SEMANTIC_FAST_ALLOWED_INTENTS = frozenset({"greeting", "ack"})


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


def ensure_v1_app(runtime: Any) -> Any:
    if runtime._v1_app is not None:
        return runtime._v1_app
    from xinyu_v1.app import XinYuV1App
    from xinyu_v1.config import XinYuV1Config

    runtime._v1_app = XinYuV1App(XinYuV1Config.load(runtime.xinyu_dir))
    return runtime._v1_app


def owner_private_semantic_fast_decision(runtime: Any, payload: dict[str, Any], text: str) -> dict[str, Any]:
    if not getattr(runtime, "owner_private_semantic_fast_route", True):
        return {"allowed": False, "notes": ["owner_private_semantic_fast_route_disabled"]}
    if not runtime._owner_private_payload_matches(payload):
        return {"allowed": False, "notes": ["not_owner_private"]}
    if v1_canary_gate.payload_has_attachment_signal(payload):
        return {"allowed": False, "notes": ["attachment_present"]}
    raw_text = _safe_str(text)
    compact = "".join(raw_text.split())
    if not compact:
        return {"allowed": False, "notes": ["empty_text"]}
    if "\n" in raw_text or "\r" in raw_text:
        return {"allowed": False, "notes": ["multiline_text"]}
    if len(compact) > 20:
        return {"allowed": False, "notes": ["text_too_long_for_semantic_fast_route"]}

    app = ensure_v1_app(runtime)
    v1_payload = dict(payload)
    v1_payload.setdefault("text", text)
    metadata = v1_payload.get("metadata")
    v1_payload["metadata"] = dict(metadata) if isinstance(metadata, dict) else {}
    v1_payload["metadata"]["is_owner_user"] = True
    v1_payload["metadata"]["v1_semantic_fast_source"] = "xinyu_core_bridge"
    turn = app.normalizer.normalize(v1_payload)
    decision = app.router.decide(turn)
    classification = decision.classification
    route = _safe_str(getattr(decision.route, "value", decision.route))
    intents = tuple(_safe_str(intent) for intent in classification.intents)
    intent_set = {intent for intent in intents if intent}
    if (
        route == "fast_path"
        and intent_set
        and intent_set.issubset(SEMANTIC_FAST_ALLOWED_INTENTS)
        and not classification.needs_model
        and not classification.needs_memory
    ):
        return {
            "allowed": True,
            "route": route,
            "intents": intents,
            "reasons": tuple(_safe_str(reason) for reason in decision.reasons),
            "notes": ["semantic_fast_allowed", f"semantic_fast_intents:{','.join(intents)}"],
        }
    return {
        "allowed": False,
        "route": route,
        "intents": intents,
        "reasons": tuple(_safe_str(reason) for reason in decision.reasons),
        "notes": ["semantic_fast_not_low_risk", f"semantic_fast_intents:{','.join(intents) or 'none'}"],
    }


async def handle_owner_private_semantic_fast_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session: Any,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    before_memory: dict[str, Any] | None,
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    decision: dict[str, Any] | None = None,
    record_decision_stage: bool = True,
) -> dict[str, Any] | None:
    started = time.perf_counter()
    if decision is None:
        try:
            decision = owner_private_semantic_fast_decision(runtime, payload, text)
        except Exception as exc:
            print(f"[xinyu_core_bridge] semantic fast route failed: {type(exc).__name__}: {exc}", flush=True)
            return None
    if not decision.get("allowed"):
        return None
    if record_decision_stage:
        record_turn_route_stage(
            runtime.xinyu_dir,
            turn_id=turn_id,
            stage="route_decided",
            route="owner_private_semantic_fast",
            status="accepted",
            elapsed_ms=int((time.perf_counter() - turn_started_at) * 1000),
            payload=payload,
            notes=[_safe_str(note) for note in decision.get("notes", [])[:4]],
        )

    try:
        rendered = await runtime._render_outward_reply(
            session.agent,
            payload=payload,
            user_text=text,
            draft_reply="",
            canonical_recall_context="",
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] semantic fast renderer failed: {type(exc).__name__}: {exc}", flush=True)
        return None

    reply = _safe_str(rendered).strip()
    if not reply:
        return None

    guarded_reply, guard_flags = runtime.speech_controller.final_reply_guard(
        payload=payload,
        user_text=text,
        reply=reply,
    )
    if not guarded_reply:
        return None
    reply = normalize_bridge_reply(guarded_reply)
    visible_dedupe = dedupe_visible_reply(reply)
    reply = visible_dedupe.text
    if not reply:
        return None

    try:
        runtime._replace_last_assistant_message(session.agent, reply)
    except Exception:
        pass
    try:
        runtime._append_dialogue_tail(session, user_text=text, reply=reply, payload=payload)
    except Exception as exc:
        print(f"[xinyu_core_bridge] semantic fast dialogue tail failed: {type(exc).__name__}: {exc}", flush=True)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    total_elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
    intents = tuple(_safe_str(intent) for intent in decision.get("intents", ()))
    notes: list[str] = [
        "owner_private_semantic_fast_intercepted",
        f"semantic_fast_route:{_safe_str(decision.get('route'), 'fast_path')}",
        f"semantic_fast_elapsed_ms:{elapsed_ms}",
    ]
    if intents:
        notes.append(f"semantic_fast_intents:{','.join(intents)}")
    notes.extend(_safe_str(note) for note in decision.get("notes", [])[:3])
    notes.extend(_safe_str(note) for note in event_sidecar.get("notes", [])[:3])
    if guard_flags:
        notes.append("final_reply_guard_flags:" + ",".join(guard_flags[:3]))
    notes.extend(_safe_str(note) for note in visible_dedupe.notes[:3])
    if cleanup.get("cleaned_sessions"):
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")

    if before_memory is None:
        memory_changed = False
        notes.append("semantic_fast_memory_snapshot_skipped")
    else:
        after_memory = _memory_snapshot(runtime.memory_root)
        memory_changed = before_memory != after_memory
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=turn_id,
        reply=reply,
        elapsed_ms=total_elapsed_ms,
        status="ok",
        notes=notes,
        memory_changed=memory_changed,
    )
    record_turn_route_stage(
        runtime.xinyu_dir,
        turn_id=turn_id,
        stage="route_finished",
        route="owner_private_semantic_fast",
        status="ok",
        elapsed_ms=total_elapsed_ms,
        payload=payload,
        notes=notes[:8],
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
        "semantic_fast": {
            "scope": "owner_private_greeting_ack",
            "route": _safe_str(decision.get("route"), "fast_path"),
            "intents": list(intents),
            "elapsed_ms": elapsed_ms,
            "renderer": "outward_reply",
        },
        "notes": notes,
    }
