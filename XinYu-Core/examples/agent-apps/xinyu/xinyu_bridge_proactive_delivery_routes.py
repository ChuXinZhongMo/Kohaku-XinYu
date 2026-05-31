from __future__ import annotations

import asyncio
import time
from datetime import datetime
from http import HTTPStatus
from typing import Any

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_proactive import acknowledge as proactive_ack_bridge
from xinyu_bridge_proactive import claim_or_preview as proactive_bridge
from xinyu_bridge_state_text import read_text_safe as _read_text_safe
from xinyu_bridge_state_text import state_field as _state_field
from xinyu_bridge_values import as_int as _as_int
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_dialogue_archive import archive_message
from xinyu_proactive_context_adapter import runtime_owner_private_turns
from xinyu_proactive_presence import acknowledge_proactive_qq_message
from xinyu_proactive_presence import claim_proactive_qq_message
from xinyu_qq_outbox import ack_qq_outbox_message
from xinyu_qq_outbox import claim_next_qq_outbox_message
from xinyu_visible_persona_voice import compose_proactive_visible_message


def _ensure_open(runtime: Any) -> None:
    if runtime._closed:
        raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")


def _ensure_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return dict(payload or {})


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


def _runtime_recent_proactive_context(runtime: Any, proactive: dict[str, Any]) -> list[Any]:
    recent_turns: list[Any] = runtime_owner_private_turns(runtime, limit=4)
    return [
        *recent_turns,
        _safe_str(proactive.get("focus_label")),
        _safe_str(proactive.get("evidence_label")),
        _safe_str(proactive.get("reason")),
    ]


async def proactive(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    try:
        result = await proactive_bridge(
            xinyu_dir=runtime.xinyu_dir,
            memory_root=runtime.memory_root,
            payload=payload,
            proactive_min_interval_seconds=runtime.proactive_min_interval_seconds,
            cleanup_idle_sessions=runtime._cleanup_idle_sessions,
            session_count=lambda: len(runtime._sessions),
            lock=runtime._global_turn_lock,
        )
        if result.get("candidate_claimed"):
            await runtime._desktop_publish_proactive_delivery_from_state(
                status_override="claimed",
                notes=[_safe_str(note) for note in result.get("notes", [])[:4]],
            )
        elif _safe_str(result.get("preview_reply") or result.get("candidate_message")).strip():
            await runtime._desktop_publish_proactive_candidate_ready_from_state(
                notes=[_safe_str(note) for note in result.get("notes", [])[:4]],
            )
        return result
    except ValueError as exc:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, str(exc)) from exc


async def proactive_ack(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    result = await proactive_ack_bridge(
        xinyu_dir=runtime.xinyu_dir,
        memory_root=runtime.memory_root,
        payload=payload,
        cleanup_idle_sessions=runtime._cleanup_idle_sessions,
        session_count=lambda: len(runtime._sessions),
        lock=runtime._global_turn_lock,
    )
    if result.get("ack_recorded"):
        await runtime._desktop_publish_proactive_delivery_from_state(
            status_override=_safe_str(result.get("ack_status"), "sent"),
            notes=[_safe_str(note) for note in result.get("notes", [])[:4]],
            severity="error" if _safe_str(result.get("ack_status")) == "failed" else None,
        )
    return result


async def qq_outbox_claim(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    claim = await asyncio.to_thread(claim_next_qq_outbox_message, runtime.xinyu_dir, payload)
    if claim.get("message_claimed"):
        return claim

    proactive_claim = await runtime._claim_proactive_for_qq_outbox(payload)
    if proactive_claim is None:
        return claim
    await runtime._desktop_publish_proactive_delivery_from_state(
        status_override="claimed",
        notes=["proactive_request_claimed_via_outbox"],
    )
    return proactive_claim


def qq_outbox_claim_fast(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    claim = claim_next_qq_outbox_message(runtime.xinyu_dir, payload)
    if claim.get("message_claimed"):
        return claim
    proactive_claim = runtime._claim_proactive_for_qq_outbox_sync(payload)
    if proactive_claim is None:
        return claim
    runtime._desktop_publish_proactive_delivery_from_state_threadsafe(
        status_override="claimed",
        notes=["proactive_request_claimed_via_outbox_fast"],
    )
    return proactive_claim


async def qq_outbox_ack(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    message_id = _safe_str(payload.get("message_id")).strip()
    if message_id.startswith("proactive:"):
        result = await proactive_ack_bridge(
            xinyu_dir=runtime.xinyu_dir,
            memory_root=runtime.memory_root,
            payload=payload,
            cleanup_idle_sessions=runtime._cleanup_idle_sessions,
            session_count=lambda: len(runtime._sessions),
            lock=runtime._global_turn_lock,
        )
        if result.get("ack_recorded"):
            await runtime._desktop_publish_proactive_delivery_from_state(
                status_override=_safe_str(result.get("ack_status"), "sent"),
                notes=[_safe_str(note) for note in result.get("notes", [])[:4]],
                severity="error" if _safe_str(result.get("ack_status")) == "failed" else None,
            )
        if result.get("ack_recorded") and result.get("ack_status") == "sent":
            runtime._record_proactive_outbound_dialogue(payload)
        return result
    return await asyncio.to_thread(ack_qq_outbox_message, runtime.xinyu_dir, payload)


def qq_outbox_ack_fast(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ensure_open(runtime)
    payload = _ensure_payload(payload)
    message_id = _safe_str(payload.get("message_id")).strip()
    if message_id.startswith("proactive:"):
        result = acknowledge_proactive_qq_message(
            runtime.xinyu_dir,
            claim_id=_safe_str(payload.get("claim_id")).strip(),
            ack_status=_safe_str(payload.get("ack_status") or payload.get("status"), "sent").strip(),
            adapter_message_id=_safe_str(payload.get("adapter_message_id") or payload.get("message_id")).strip(),
            adapter_error=_safe_str(payload.get("adapter_error") or payload.get("error")).strip(),
        )
        result = {**result, "session_created": False, "sessions": len(runtime._sessions)}
        if result.get("ack_recorded"):
            runtime._desktop_publish_proactive_delivery_from_state_threadsafe(
                status_override=_safe_str(result.get("ack_status"), "sent"),
                notes=[_safe_str(note) for note in result.get("notes", [])[:4]],
                severity="error" if _safe_str(result.get("ack_status")) == "failed" else None,
            )
        if result.get("ack_recorded") and result.get("ack_status") == "sent":
            runtime._record_proactive_outbound_dialogue(payload)
        return result
    return ack_qq_outbox_message(runtime.xinyu_dir, payload)


async def claim_proactive_for_qq_outbox(runtime: Any, payload: dict[str, Any]) -> dict[str, Any] | None:
    candidate = runtime._ready_proactive_outbox_candidate()
    if not candidate:
        return None

    owner_user_id = runtime._owner_private_user_id()
    if not owner_user_id:
        return None

    claim_id = _safe_str(payload.get("claim_id")).strip() or f"proactive-{int(time.time())}"
    proactive = await proactive_bridge(
        xinyu_dir=runtime.xinyu_dir,
        memory_root=runtime.memory_root,
        payload={
            "claim": True,
            "claim_id": claim_id,
            "min_interval_seconds": payload.get("min_interval_seconds", runtime.proactive_min_interval_seconds),
        },
        proactive_min_interval_seconds=runtime.proactive_min_interval_seconds,
        cleanup_idle_sessions=runtime._cleanup_idle_sessions,
        session_count=lambda: len(runtime._sessions),
        lock=runtime._global_turn_lock,
    )
    if not proactive.get("candidate_claimed"):
        return None

    message = compose_proactive_visible_message(
        proactive.get("reply") or proactive.get("preview_reply"),
        source="proactive_qq_claim",
        recent_context=_runtime_recent_proactive_context(runtime, proactive),
    ).strip()
    if not message:
        return None
    request_id = _safe_str(proactive.get("proactive_request_id") or proactive.get("request_id")).strip()
    if not request_id:
        request_id = _safe_str(proactive.get("evaluated_at")).strip() or claim_id
    return {
        "accepted": True,
        "message_claimed": True,
        "message_id": f"proactive:{request_id}",
        "claim_id": claim_id,
        "target": {"message_kind": "private", "user_id": owner_user_id, "group_id": ""},
        "message": message,
        "attempts": 1,
        "source": "proactive_request",
        "notes": ["claimed", "proactive_request_claimed_via_outbox"] + list(proactive.get("notes", [])),
    }


def claim_proactive_for_qq_outbox_sync(runtime: Any, payload: dict[str, Any]) -> dict[str, Any] | None:
    candidate = runtime._ready_proactive_outbox_candidate()
    if not candidate:
        return None

    owner_user_id = runtime._owner_private_user_id()
    if not owner_user_id:
        return None

    claim_id = _safe_str(payload.get("claim_id")).strip() or f"proactive-{int(time.time())}"
    min_interval_seconds = _as_int(payload.get("min_interval_seconds"), runtime.proactive_min_interval_seconds)
    proactive = claim_proactive_qq_message(
        runtime.xinyu_dir,
        mode="bridge_proactive_qq_claim_fast",
        claim=True,
        claim_id=claim_id,
        min_interval_seconds=min_interval_seconds,
    )
    if not proactive.get("candidate_claimed"):
        return None

    message = compose_proactive_visible_message(
        proactive.get("reply") or proactive.get("preview_reply"),
        source="proactive_qq_claim_fast",
        recent_context=_runtime_recent_proactive_context(runtime, proactive),
    ).strip()
    if not message:
        return None
    request_id = _safe_str(proactive.get("proactive_request_id") or proactive.get("request_id")).strip()
    if not request_id or request_id in {"none", "unknown"}:
        request_id = _safe_str(proactive.get("evaluated_at")).strip() or claim_id
    return {
        "accepted": True,
        "message_claimed": True,
        "message_id": f"proactive:{request_id}",
        "claim_id": claim_id,
        "target": {"message_kind": "private", "user_id": owner_user_id, "group_id": ""},
        "message": message,
        "attempts": 1,
        "source": "proactive_request",
        "notes": ["claimed", "proactive_request_claimed_via_outbox_fast"] + list(proactive.get("notes", [])),
    }


def ready_proactive_outbox_candidate(runtime: Any) -> str:
    state = _read_text_safe(runtime.xinyu_dir / "memory/context/proactive_request_state.md")
    if _state_field(state, "status") != "ready":
        return ""
    if _state_field(state, "delivery_level") not in {"queue_owner_private", "claim_ack"}:
        return ""
    candidate = _state_field(state, "concrete_question")
    return candidate if candidate not in {"", "none", "unknown"} else ""


def proactive_candidate_already_handled(runtime: Any, candidate: str) -> bool:
    state = _read_text_safe(runtime.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
    status = _state_field(state, "last_claim_status")
    if status not in {"claimed", "sent"}:
        return False
    return _state_field(state, "last_claimed_message") == candidate


def record_proactive_outbound_dialogue(runtime: Any, ack_payload: dict[str, Any]) -> None:
    dispatch = _read_text_safe(runtime.xinyu_dir / "memory/context/proactive_qq_dispatch_state.md")
    if _state_field(dispatch, "last_ack_status") != "sent":
        return
    message = _state_field(dispatch, "last_claimed_message")
    if not message or message in {"none", "unknown"}:
        return
    claimed_at = _timestamp_or_now_iso(_state_field(dispatch, "last_claimed_at"))
    payload = runtime._owner_private_payload(
        source="proactive_request_outbox",
        message_id=_safe_str(ack_payload.get("message_id")),
    )
    appended = runtime._append_assistant_to_dialogue_tail(
        payload["session_id"],
        message,
        recorded_at=_timestamp_or_now_iso(claimed_at),
    )
    if not appended:
        return
    try:
        archive_message(
            runtime.xinyu_dir,
            payload,
            role="assistant",
            text=message,
            created_at=_timestamp_or_now_iso(claimed_at),
            message_type="private_proactive",
            metadata={"source": "proactive_request_outbox"},
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] proactive outbound archive failed: {exc}", flush=True)
