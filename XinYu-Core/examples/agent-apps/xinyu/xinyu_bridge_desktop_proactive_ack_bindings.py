from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

import xinyu_bridge_desktop_proactive_ack as _proactive_ack
from xinyu_bridge_desktop_proactive_deps_support import DesktopProactiveDeps


def record_desktop_initiative_feedback(
    runtime: Any,
    item: dict[str, Any],
    *,
    action: str,
    deps: DesktopProactiveDeps,
    record_feedback: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not deps.as_bool(item.get("initiativeLifecycle"), default=False):
        return {}
    try:
        feedback_func = record_feedback or deps.record_initiative_feedback
        return feedback_func(
            runtime.xinyu_dir,
            candidate_id=deps.safe_str(item.get("candidateId")),
            action=action,
            feedback_at=datetime.now().astimezone().isoformat(),
            details={
                "source": "desktop_proactive_ack",
                "status": deps.safe_str(item.get("status")),
                "deliveryLevel": deps.safe_str(item.get("deliveryLevel")),
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
    deps: DesktopProactiveDeps,
) -> dict[str, Any]:
    return await _proactive_ack.desktop_finish_proactive_ack(
        runtime,
        item,
        action=action,
        status=status,
        answer_state=answer_state,
        ack_status=ack_status,
        notes=notes,
        adapter_message_id=adapter_message_id,
        adapter_error=adapter_error,
        extra=extra,
        claim_id=claim_id,
        safe_str_func=deps.safe_str,
    )
