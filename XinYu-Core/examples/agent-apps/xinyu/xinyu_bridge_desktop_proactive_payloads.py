from __future__ import annotations

from http import HTTPStatus
from typing import Any, Callable

from xinyu_bridge_errors import BridgeRequestError


DESKTOP_PROACTIVE_ACK_ACTIONS = {"read_locally", "approve_qq", "dismiss", "reply"}


def ensure_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is not None and not isinstance(payload, dict):
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
    return dict(payload or {})


def normalize_desktop_proactive_ack_payload(
    payload: dict[str, Any] | None,
    *,
    safe_str: Callable[..., str],
    ensure_payload_func: Callable[[dict[str, Any] | None], dict[str, Any]] = ensure_payload,
    ack_actions: set[str] = DESKTOP_PROACTIVE_ACK_ACTIONS,
) -> tuple[str, str]:
    body = ensure_payload_func(payload)
    candidate_id = safe_str(body.get("candidateId") or body.get("candidate_id") or body.get("requestId")).strip()
    action = safe_str(body.get("action")).strip().lower()
    if not candidate_id:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "missing candidateId")
    if action not in ack_actions:
        raise BridgeRequestError(HTTPStatus.BAD_REQUEST, "invalid desktop proactive action")
    return candidate_id, action
