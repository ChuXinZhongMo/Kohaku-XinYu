from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_proactive_delivery_contract import proactive_outbox_message_id


def runtime_recent_proactive_context(
    runtime: Any,
    proactive: dict[str, Any],
    *,
    owner_private_turns_func: Callable[..., list[Any]],
    safe_str_func: Callable[..., str],
) -> list[Any]:
    recent_turns: list[Any] = owner_private_turns_func(runtime, limit=4)
    return [
        *recent_turns,
        safe_str_func(proactive.get("focus_label")),
        safe_str_func(proactive.get("evidence_label")),
        safe_str_func(proactive.get("reason")),
    ]


def owner_private_share_blocks(
    runtime: Any,
    *,
    load_share_block_reasons_func: Callable[..., list[str]],
) -> list[str]:
    try:
        return load_share_block_reasons_func(runtime.xinyu_dir)
    except Exception:
        return ["owner_private_autonomous_share_unreadable"]


def build_proactive_claim_message(
    runtime: Any,
    proactive: dict[str, Any],
    *,
    source: str,
    owner_private_turns_func: Callable[..., list[Any]],
    compose_visible_message_func: Callable[..., str],
    safe_str_func: Callable[..., str],
) -> str:
    return compose_visible_message_func(
        proactive.get("reply") or proactive.get("preview_reply"),
        source=source,
        recent_context=runtime_recent_proactive_context(
            runtime,
            proactive,
            owner_private_turns_func=owner_private_turns_func,
            safe_str_func=safe_str_func,
        ),
    ).strip()


def build_proactive_claim_result(
    proactive: dict[str, Any],
    *,
    claim_id: str,
    owner_user_id: str,
    message: str,
    note: str,
    safe_str_func: Callable[..., str],
    fallback_unknown: bool = False,
) -> dict[str, Any]:
    request_id = safe_str_func(proactive.get("proactive_request_id") or proactive.get("request_id")).strip()
    if not request_id or (fallback_unknown and request_id in {"none", "unknown"}):
        request_id = safe_str_func(proactive.get("evaluated_at")).strip() or claim_id
    return {
        "accepted": True,
        "message_claimed": True,
        "message_id": proactive_outbox_message_id(request_id),
        "claim_id": claim_id,
        "target": {"message_kind": "private", "user_id": owner_user_id, "group_id": ""},
        "message": message,
        "attempts": 1,
        "source": "proactive_request",
        "notes": ["claimed", note] + list(proactive.get("notes", [])),
    }
