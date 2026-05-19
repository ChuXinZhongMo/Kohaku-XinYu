from __future__ import annotations

import asyncio
import time
from datetime import datetime
from http import HTTPStatus
from typing import Any, Callable

from state_service import atomic_write_text
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_state_text import read_text_safe as _read_text_safe
from xinyu_bridge_values import as_bool as _as_bool
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_initiative_orchestrator import record_initiative_feedback
from xinyu_proactive_presence import _write_dispatch_state as write_proactive_qq_dispatch_state
from xinyu_qq_outbox import enqueue_qq_outbox_message
from xinyu_visible_persona_voice import compose_proactive_visible_message


DESKTOP_PROACTIVE_INBOX_MAX = 50
DESKTOP_PROACTIVE_HISTORY_MAX = 20
DESKTOP_PROACTIVE_ACK_ACTIONS = {"read_locally", "approve_qq", "dismiss", "reply"}


def _ensure_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return dict(payload or {})


async def desktop_proactive_inbox(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _ = payload
    runtime._desktop_load_proactive_history()
    state_item = runtime._desktop_proactive_item_from_state()
    if state_item:
        runtime._desktop_upsert_proactive_inbox(state_item)
    else:
        runtime._desktop_remove_proactive_state_items()
    with runtime._desktop_proactive_lock:
        items = sorted(
            (dict(item) for item in runtime._desktop_proactive_inbox.values()),
            key=lambda item: _safe_str(item.get("createdAt")),
            reverse=True,
        )[:DESKTOP_PROACTIVE_INBOX_MAX]
        history = sorted(
            (dict(item) for item in runtime._desktop_proactive_history),
            key=lambda item: _safe_str(item.get("updatedAt") or item.get("handledAt") or item.get("createdAt")),
            reverse=True,
        )[:DESKTOP_PROACTIVE_HISTORY_MAX]
    return {
        "version": 1,
        "items": items,
        "history": history,
        "notes": ["desktop_proactive_inbox_v0_runtime_buffer"],
    }


async def desktop_proactive_ack(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if runtime._closed:
        raise BridgeRequestError(HTTPStatus.SERVICE_UNAVAILABLE, "bridge is shutting down")
    payload = _ensure_payload(payload)
    candidate_id = _safe_str(payload.get("candidateId") or payload.get("candidate_id") or payload.get("requestId")).strip()
    action = _safe_str(payload.get("action")).strip().lower()
    if not candidate_id:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "missing candidateId")
    if action not in DESKTOP_PROACTIVE_ACK_ACTIONS:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "invalid desktop proactive action")

    item = runtime._desktop_proactive_item_from_state(include_final=True)
    if not item:
        item = runtime._desktop_proactive_existing(candidate_id)
    if not item or _safe_str(item.get("candidateId")) != candidate_id:
        raise BridgeRequestError(HTTPStatus.NOT_FOUND, "desktop proactive candidate not found")
    runtime._record_desktop_initiative_feedback(item, action=action)

    if action == "read_locally":
        return await runtime._desktop_finish_proactive_ack(
            item,
            action="read_locally",
            status="read_locally",
            answer_state="read_locally",
            ack_status="read_locally",
            notes=["desktop_read_locally"],
        )
    if action == "dismiss":
        return await runtime._desktop_finish_proactive_ack(
            item,
            action="dismiss",
            status="dismissed",
            answer_state="dismissed",
            ack_status="dismissed",
            notes=["desktop_dismissed"],
        )
    if action == "reply":
        return await runtime._desktop_finish_proactive_ack(
            item,
            action="reply",
            status="answered",
            answer_state="owner_replied",
            ack_status="replied",
            notes=["desktop_owner_replied_to_proactive"],
        )
    return await runtime._desktop_approve_proactive_qq(item)


def record_desktop_initiative_feedback(
    runtime: Any,
    item: dict[str, Any],
    *,
    action: str,
    record_feedback: Callable[..., dict[str, Any]] = record_initiative_feedback,
) -> dict[str, Any]:
    if not _as_bool(item.get("initiativeLifecycle"), default=False):
        return {}
    try:
        return record_feedback(
            runtime.xinyu_dir,
            candidate_id=_safe_str(item.get("candidateId")),
            action=action,
            feedback_at=datetime.now().astimezone().isoformat(),
            details={
                "source": "desktop_proactive_ack",
                "status": _safe_str(item.get("status")),
                "deliveryLevel": _safe_str(item.get("deliveryLevel")),
                "claimable": bool(item.get("claimable")),
            },
        )
    except Exception as exc:
        runtime._trace_autonomous(f"initiative_feedback_error={exc!r}")
        return {"accepted": False, "recorded": False, "notes": [f"initiative_feedback_error:{type(exc).__name__}"]}


async def desktop_finish_proactive_ack(
    runtime: Any,
    item: dict[str, Any],
    *,
    action: str,
    status: str,
    answer_state: str,
    ack_status: str,
    notes: list[str],
    adapter_message_id: str = "",
    adapter_error: str = "",
    extra: dict[str, Any] | None = None,
    claim_id: str = "",
) -> dict[str, Any]:
    candidate_id = _safe_str(item.get("candidateId"))
    updated = runtime._desktop_update_proactive_request_state(
        candidate_id=candidate_id,
        status=status,
        answer_state=answer_state,
        ack_status=ack_status,
        adapter_message_id=adapter_message_id,
        adapter_error=adapter_error,
        claim_id=claim_id,
    )
    event_item = (
        {**item, **updated, **(extra or {}), "desktopAction": action}
        if updated
        else {**item, **(extra or {}), "desktopAction": action}
    )
    event = await runtime._desktop_publish_proactive_delivery_item(
        event_item,
        status_override=status,
        notes=notes,
        severity="error" if status == "failed" else None,
    )
    return {
        "accepted": True,
        "ack_recorded": True,
        "candidateId": candidate_id,
        "action": action,
        "status": status,
        "eventId": _safe_str(event.get("id")),
        **(extra or {}),
        "notes": notes + (["proactive_request_state_updated"] if updated else ["proactive_request_state_not_updated"]),
    }


async def desktop_approve_proactive_qq(runtime: Any, item: dict[str, Any]) -> dict[str, Any]:
    candidate_id = _safe_str(item.get("candidateId"))
    if not bool(item.get("claimable")):
        return {
            "accepted": False,
            "ack_recorded": False,
            "candidateId": candidate_id,
            "action": "approve_qq",
            "status": _safe_str(item.get("status")),
            "notes": ["desktop_proactive_candidate_not_qq_claimable"],
        }
    owner_user_id = runtime._owner_private_user_id()
    if not owner_user_id:
        return {
            "accepted": False,
            "ack_recorded": False,
            "candidateId": candidate_id,
            "action": "approve_qq",
            "notes": ["missing_owner_user_id"],
        }
    message = compose_proactive_visible_message(
        item.get("candidatePreview"),
        source="desktop_approve_qq",
    ).strip()
    if not message:
        return {
            "accepted": False,
            "ack_recorded": False,
            "candidateId": candidate_id,
            "action": "approve_qq",
            "notes": ["missing_candidate_message"],
        }
    queued = await asyncio.to_thread(
        enqueue_qq_outbox_message,
        runtime.xinyu_dir,
        user_id=owner_user_id,
        message=message,
        source="desktop_proactive_ack",
        dedupe_key=f"desktop-proactive:{candidate_id}",
        metadata={
            "source": "xinyu_desktop_shell",
            "desktop_candidate_id": candidate_id,
            "proactive_request_id": _safe_str(item.get("requestId")),
            "desktop_action": "approve_qq",
        },
    )
    if not queued.get("accepted"):
        return {
            "accepted": False,
            "ack_recorded": False,
            "candidateId": candidate_id,
            "action": "approve_qq",
            "notes": ["qq_outbox_enqueue_failed"] + [_safe_str(note) for note in queued.get("notes", [])],
        }
    outbox_message_id = _safe_str(queued.get("message_id"))
    claim_id = f"desktop-proactive-{int(time.time())}"
    write_proactive_qq_dispatch_state(
        runtime.xinyu_dir,
        claimed_at=datetime.now().astimezone().isoformat(),
        claim_id=claim_id,
        candidate=message,
        request_id=_safe_str(item.get("requestId"), "none") or "none",
        min_interval_seconds=runtime.proactive_min_interval_seconds,
    )
    return await runtime._desktop_finish_proactive_ack(
        item,
        action="approve_qq",
        status="queued_qq",
        answer_state="approved_qq",
        ack_status="queued",
        adapter_message_id=outbox_message_id,
        notes=["desktop_approved_qq"] + [_safe_str(note) for note in queued.get("notes", [])],
        extra={
            "outboxMessageId": outbox_message_id,
            "queued": bool(queued.get("queued")),
        },
        claim_id=claim_id,
    )


def desktop_update_proactive_request_state(
    runtime: Any,
    *,
    candidate_id: str,
    status: str,
    answer_state: str = "",
    ack_status: str = "",
    adapter_message_id: str = "",
    adapter_error: str = "",
    claim_id: str = "",
) -> dict[str, Any]:
    path = runtime.xinyu_dir / "memory/context/proactive_request_state.md"
    state = _read_text_safe(path)
    if not state:
        return {}
    current = runtime._desktop_proactive_item_from_state(include_final=True)
    if _safe_str(current.get("candidateId")) != candidate_id:
        return {}
    updated_at = datetime.now().astimezone().isoformat()
    updated = runtime._desktop_replace_frontmatter_field(state, "updated_at", updated_at)
    updated = runtime._desktop_replace_list_field(updated, "status", status)
    if answer_state:
        updated = runtime._desktop_replace_list_field(updated, "request_answer_state", answer_state)
    if ack_status:
        updated = runtime._desktop_replace_list_field(updated, "last_ack_status", ack_status)
    if claim_id:
        updated = runtime._desktop_replace_list_field(updated, "last_claim_id", claim_id)
    if adapter_message_id:
        updated = runtime._desktop_replace_list_field(updated, "adapter_message_id", adapter_message_id)
    if adapter_error:
        updated = runtime._desktop_replace_list_field(updated, "adapter_error", adapter_error)
    atomic_write_text(path, updated.rstrip())
    if status in {"answered", "dismissed", "read_locally"} or answer_state in {
        "owner_replied",
        "dismissed",
        "read_locally",
    }:
        runtime._refresh_initiative_spine_after_proactive_feedback(
            trigger=f"desktop_proactive_{answer_state or status}",
            checked_at=updated_at,
        )
    return runtime._desktop_proactive_item_from_state(include_final=True)
