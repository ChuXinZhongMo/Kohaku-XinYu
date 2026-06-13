from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


SafeStrFunc = Callable[..., str]
AsBoolFunc = Callable[..., bool]

AUTHORIZE_CODEX_KEYS = (
    "authorizeCodex",
    "authorize_codex",
    "authorizeExecution",
    "authorize_execution",
    "allowCodex",
    "allow_codex",
)
AUTHORIZE_EXISTING_KEYS = (
    "authorizeExisting",
    "authorize_existing",
    "authorizePrepared",
    "authorize_prepared",
)
DECISION_ALIASES = {
    "approve": "approved",
    "ok": "approved",
    "accept": "approved",
    "deny": "denied",
    "reject": "denied",
    "rejected": "denied",
}
APPROVAL_DECISIONS = {"approved", "denied"}


@dataclass(frozen=True, slots=True)
class DesktopSelfActionApprovalPayload:
    queue_id: str
    decision: str
    reason: str
    execute: bool
    decided_by: str
    authorize_codex: bool
    authorize_existing: bool
    timeout_seconds: int


def parse_desktop_self_action_approval_payload(
    payload: dict[str, Any] | None,
    *,
    request_error_type: Callable[[Any, str], Exception],
    bad_request_status: Any,
    safe_str_func: SafeStrFunc,
    as_bool_func: AsBoolFunc,
) -> DesktopSelfActionApprovalPayload:
    if payload is not None and not isinstance(payload, dict):
        raise request_error_type(bad_request_status, "request body must be a JSON object")
    body = payload or {}
    decision = normalize_self_action_approval_decision(body.get("decision"), safe_str_func=safe_str_func)
    if decision not in APPROVAL_DECISIONS:
        raise request_error_type(bad_request_status, "invalid self action approval decision")

    execute = as_bool_func(body.get("execute"), default=decision == "approved")
    authorize_codex = decision == "approved" and execute and as_bool_func(
        first_present_payload_value(body, AUTHORIZE_CODEX_KEYS),
        default=False,
    )
    authorize_existing = decision == "approved" and execute and as_bool_func(
        first_present_payload_value(body, AUTHORIZE_EXISTING_KEYS),
        default=False,
    )
    return DesktopSelfActionApprovalPayload(
        queue_id=safe_str_func(body.get("queueId") or body.get("queue_id") or "latest").strip() or "latest",
        decision=decision,
        reason=safe_str_func(body.get("reason") or body.get("note")).strip(),
        execute=execute,
        decided_by=safe_str_func(body.get("decidedBy") or body.get("decided_by") or "owner_desktop").strip()
        or "owner_desktop",
        authorize_codex=authorize_codex,
        authorize_existing=authorize_existing,
        timeout_seconds=parse_timeout_seconds(
            safe_str_func(body.get("timeoutSeconds") or body.get("timeout_seconds") or "1800").strip()
        ),
    )


def normalize_self_action_approval_decision(value: Any, *, safe_str_func: SafeStrFunc) -> str:
    decision = safe_str_func(value).strip().lower()
    return DECISION_ALIASES.get(decision, decision)


def first_present_payload_value(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def parse_timeout_seconds(value: str) -> int:
    try:
        return max(30, min(3600, int(value)))
    except ValueError:
        return 1800


def resolve_desktop_self_action_pending_item(
    listed: dict[str, Any],
    queue_id: str,
    *,
    safe_str_func: SafeStrFunc,
) -> dict[str, Any]:
    items = listed.get("items") if isinstance(listed.get("items"), list) else []
    pending = [
        item
        for item in items
        if isinstance(item, dict) and safe_str_func(item.get("status")) == "pending_owner_approval"
    ]
    resolved_queue_id = queue_id
    if queue_id in {"", "latest", "next"}:
        queue = listed.get("approval_queue") if isinstance(listed.get("approval_queue"), dict) else {}
        resolved_queue_id = safe_str_func(queue.get("latest_pending_queue_id"))
    for item in pending:
        if safe_str_func(item.get("queue_id")) == resolved_queue_id:
            return item
    return pending[-1] if pending else {}
