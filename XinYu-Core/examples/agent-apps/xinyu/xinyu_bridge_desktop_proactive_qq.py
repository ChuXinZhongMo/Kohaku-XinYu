from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, Callable


async def desktop_approve_proactive_qq(
    runtime: Any,
    item: dict[str, Any],
    *,
    owner_private_turns_func: Callable[..., list[Any]],
    current_question_func: Callable[..., str],
    compose_visible_message_func: Callable[..., str],
    enqueue_qq_outbox_message_func: Callable[..., dict[str, Any]],
    write_dispatch_state_func: Callable[..., Any],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    candidate_id = safe_str_func(item.get("candidateId"))
    if not bool(item.get("claimable")):
        return {
            "accepted": False,
            "ack_recorded": False,
            "candidateId": candidate_id,
            "action": "approve_qq",
            "status": safe_str_func(item.get("status")),
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
    recent_turns = owner_private_turns_func(runtime, limit=4)
    current_question = current_question_func(runtime, item)
    message = current_question or compose_visible_message_func(
        item.get("candidatePreview"),
        source="desktop_approve_qq",
        recent_context=[
            *recent_turns,
            safe_str_func(item.get("focusLabel")),
            safe_str_func(item.get("whyNowPreview")),
        ],
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
        enqueue_qq_outbox_message_func,
        runtime.xinyu_dir,
        user_id=owner_user_id,
        message=message,
        source="desktop_proactive_ack",
        dedupe_key=f"desktop-proactive:{candidate_id}",
        metadata={
            "source": "xinyu_desktop_shell",
            "desktop_candidate_id": candidate_id,
            "proactive_request_id": safe_str_func(item.get("requestId")),
            "desktop_action": "approve_qq",
        },
    )
    if not queued.get("accepted"):
        failure_notes = ["desktop_qq_enqueue_failed"] + [safe_str_func(note) for note in queued.get("notes", [])]
        recorded = await runtime._desktop_finish_proactive_ack(
            item,
            action="approve_qq",
            status="failed",
            answer_state="qq_enqueue_failed",
            ack_status="failed",
            adapter_error=";".join(note for note in failure_notes if note),
            notes=failure_notes,
            extra={"queued": False},
        )
        return {
            **recorded,
            "accepted": False,
            "ack_recorded": True,
            "candidateId": candidate_id,
            "action": "approve_qq",
            "status": "failed",
            "notes": recorded.get("notes", failure_notes),
        }
    outbox_message_id = safe_str_func(queued.get("message_id"))
    claim_id = f"desktop-proactive-{int(time.time())}"
    write_dispatch_state_func(
        runtime.xinyu_dir,
        claimed_at=datetime.now().astimezone().isoformat(),
        claim_id=claim_id,
        candidate=message,
        request_id=safe_str_func(item.get("requestId"), "none") or "none",
        min_interval_seconds=runtime.proactive_min_interval_seconds,
    )
    return await runtime._desktop_finish_proactive_ack(
        item,
        action="approve_qq",
        status="queued_qq",
        answer_state="approved_qq",
        ack_status="queued",
        adapter_message_id=outbox_message_id,
        notes=["desktop_approved_qq"] + [safe_str_func(note) for note in queued.get("notes", [])],
        extra={
            "outboxMessageId": outbox_message_id,
            "queued": bool(queued.get("queued")),
        },
        claim_id=claim_id,
    )
