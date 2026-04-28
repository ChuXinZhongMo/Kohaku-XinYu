"""Compatibility helpers for the v0.8.x bridge contract."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from ..errors import XinYuV1Error, error_to_json
from .models import BridgeReply


def bridge_success(
    reply: str,
    *,
    accepted: bool = True,
    memory_changed: bool | None = None,
    notes: tuple[str, ...] = (),
    route: str = "",
    trace_id: str = "",
    **extra: Any,
) -> dict[str, Any]:
    return BridgeReply(
        accepted=accepted,
        reply=reply,
        memory_changed=memory_changed,
        notes=notes,
        route=route,
        trace_id=trace_id,
        extra={key: value for key, value in extra.items() if value is not None},
    ).to_json()


def bridge_error(exc: BaseException) -> tuple[HTTPStatus, dict[str, Any]]:
    if isinstance(exc, XinYuV1Error):
        detail = exc.to_detail()
        return detail.status, {"accepted": False, "reply": "", "error": detail.to_json(), "notes": [detail.code]}
    data = error_to_json(exc)
    return HTTPStatus.INTERNAL_SERVER_ERROR, {"accepted": False, "reply": "", "error": data, "notes": ["unexpected_error"]}


def proactive_reply(
    *,
    reply: str,
    claim_id: str,
    accepted: bool = True,
    candidate_claimed: bool = False,
    notes: tuple[str, ...] = (),
) -> dict[str, Any]:
    return BridgeReply(
        accepted=accepted,
        reply=reply,
        claim_id=claim_id,
        candidate_claimed=candidate_claimed,
        notes=notes,
    ).to_json()

