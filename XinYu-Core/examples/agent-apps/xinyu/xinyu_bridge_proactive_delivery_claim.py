from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_proactive_delivery_routes_claim_result import (
    build_proactive_claim_message,
    build_proactive_claim_result,
    owner_private_share_blocks,
)


async def qq_outbox_claim(
    runtime: Any,
    payload: dict[str, Any],
    *,
    claim_next_message_func: Callable[..., dict[str, Any]],
    to_thread_func: Callable[..., Any],
) -> dict[str, Any]:
    claim = await to_thread_func(claim_next_message_func, runtime.xinyu_dir, payload)
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


def qq_outbox_claim_fast(
    runtime: Any,
    payload: dict[str, Any],
    *,
    claim_next_message_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    claim = claim_next_message_func(runtime.xinyu_dir, payload)
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


async def claim_proactive_for_qq_outbox(
    runtime: Any,
    payload: dict[str, Any],
    *,
    proactive_bridge_func: Callable[..., Any],
    owner_private_turns_func: Callable[..., list[Any]],
    load_share_block_reasons_func: Callable[..., list[str]],
    compose_visible_message_func: Callable[..., str],
    safe_str_func: Callable[..., str],
    time_func: Callable[[], float],
) -> dict[str, Any] | None:
    candidate = runtime._ready_proactive_outbox_candidate()
    if not candidate:
        return None
    if owner_private_share_blocks(runtime, load_share_block_reasons_func=load_share_block_reasons_func):
        return None

    owner_user_id = runtime._owner_private_user_id()
    if not owner_user_id:
        return None

    claim_id = safe_str_func(payload.get("claim_id")).strip() or f"proactive-{int(time_func())}"
    proactive = await proactive_bridge_func(
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

    message = build_proactive_claim_message(
        runtime,
        proactive,
        source="proactive_qq_claim",
        owner_private_turns_func=owner_private_turns_func,
        compose_visible_message_func=compose_visible_message_func,
        safe_str_func=safe_str_func,
    )
    if not message:
        return None
    return build_proactive_claim_result(
        proactive,
        claim_id=claim_id,
        owner_user_id=owner_user_id,
        message=message,
        note="proactive_request_claimed_via_outbox",
        safe_str_func=safe_str_func,
    )


def claim_proactive_for_qq_outbox_sync(
    runtime: Any,
    payload: dict[str, Any],
    *,
    claim_proactive_qq_message_func: Callable[..., dict[str, Any]],
    owner_private_turns_func: Callable[..., list[Any]],
    load_share_block_reasons_func: Callable[..., list[str]],
    compose_visible_message_func: Callable[..., str],
    safe_str_func: Callable[..., str],
    as_int_func: Callable[..., int],
    time_func: Callable[[], float],
) -> dict[str, Any] | None:
    candidate = runtime._ready_proactive_outbox_candidate()
    if not candidate:
        return None
    if owner_private_share_blocks(runtime, load_share_block_reasons_func=load_share_block_reasons_func):
        return None

    owner_user_id = runtime._owner_private_user_id()
    if not owner_user_id:
        return None

    claim_id = safe_str_func(payload.get("claim_id")).strip() or f"proactive-{int(time_func())}"
    min_interval_seconds = as_int_func(payload.get("min_interval_seconds"), runtime.proactive_min_interval_seconds)
    proactive = claim_proactive_qq_message_func(
        runtime.xinyu_dir,
        mode="bridge_proactive_qq_claim_fast",
        claim=True,
        claim_id=claim_id,
        min_interval_seconds=min_interval_seconds,
    )
    if not proactive.get("candidate_claimed"):
        return None

    message = build_proactive_claim_message(
        runtime,
        proactive,
        source="proactive_qq_claim_fast",
        owner_private_turns_func=owner_private_turns_func,
        compose_visible_message_func=compose_visible_message_func,
        safe_str_func=safe_str_func,
    )
    if not message:
        return None
    return build_proactive_claim_result(
        proactive,
        claim_id=claim_id,
        owner_user_id=owner_user_id,
        message=message,
        note="proactive_request_claimed_via_outbox_fast",
        safe_str_func=safe_str_func,
        fallback_unknown=True,
    )
